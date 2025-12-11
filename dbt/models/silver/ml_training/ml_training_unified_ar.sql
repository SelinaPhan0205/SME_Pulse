{{ config(
    materialized='table',
    tags=['ml_training', 'unified_dataset', 'phase4', 'retrain_ready']
) }}

-- ===================================================================
-- ML_TRAINING_UNIFIED_AR: Unified AR dataset for ML model retraining
-- 
-- Purpose: UNION historical Kaggle data + new App DB data
-- This dataset allows retraining ML models on combined data sources
-- 
-- Strategy:
--   1. Keep historical Kaggle data (already transformed in stg_ar_invoices_vn)
--   2. Add new App DB data (from stg_app_ar_invoices)
--   3. Ensure schema alignment for both sources
--   4. Mark source system for data lineage tracking
-- 
-- Use Cases:
--   - UC05: AR Priority Scoring (payment prediction)
--   - UC09: Cashflow Forecasting (Prophet model)
--   - UC10: Anomaly Detection (Isolation Forest)
-- ===================================================================

-- Historical data from Kaggle (Bronze → Silver)
WITH kaggle_invoices AS (
    SELECT
        -- ===== KEYS =====
        invoice_id,
        business_code,
        cust_number,
        
        -- ===== DATES =====
        baseline_create_date,
        due_in_date,
        clear_date,
        
        -- ===== AMOUNTS =====
        total_open_amount,
        
        -- ===== STATUS =====
        is_open,
        
        -- ===== ATTRIBUTES =====
        invoice_currency,
        cust_payment_terms,
        
        -- ===== SOURCE METADATA =====
        'KAGGLE' AS data_source,
        ingested_at,
        
        -- ===== DERIVED FEATURES (for ML) =====
        -- Days from invoice to due date
        CASE 
            WHEN due_in_date IS NOT NULL AND baseline_create_date IS NOT NULL
            THEN DATE_DIFF('day', 
                DATE_PARSE(baseline_create_date, '%Y/%m/%d'),
                DATE_PARSE(due_in_date, '%Y/%m/%d')
            )
            ELSE NULL
        END AS days_to_due,
        
        -- Days from invoice to payment (DSO - Days Sales Outstanding)
        CASE 
            WHEN clear_date IS NOT NULL AND clear_date != '' AND baseline_create_date IS NOT NULL
            THEN DATE_DIFF('day', 
                DATE_PARSE(baseline_create_date, '%Y/%m/%d'),
                DATE_PARSE(clear_date, '%Y/%m/%d')
            )
            ELSE NULL
        END AS days_to_clear,
        
        -- Overdue flag (at time of snapshot)
        CASE 
            WHEN is_open = true 
                 AND due_in_date IS NOT NULL
                 AND CURRENT_DATE > DATE_PARSE(due_in_date, '%Y/%m/%d')
            THEN TRUE
            ELSE FALSE
        END AS is_overdue
        
    FROM {{ ref('stg_ar_invoices_vn') }}
),

-- New data from App DB (OLTP → Bronze → Silver)
app_db_invoices AS (
    SELECT
        -- ===== KEYS =====
        invoice_id,
        business_code,
        cust_number,
        
        -- ===== DATES =====
        baseline_create_date,
        due_in_date,
        CAST(NULL AS VARCHAR) AS clear_date,  -- App DB doesn't track clear_date yet
        
        -- ===== AMOUNTS =====
        total_open_amount,
        
        -- ===== STATUS =====
        is_open,
        
        -- ===== ATTRIBUTES =====
        invoice_currency,
        CAST(NULL AS VARCHAR) AS cust_payment_terms,  -- App DB doesn't have payment terms
        
        -- ===== SOURCE METADATA =====
        'APP_DB' AS data_source,
        CURRENT_TIMESTAMP AS ingested_at,
        
        -- ===== DERIVED FEATURES (for ML) =====
        -- Days from invoice to due date
        CASE 
            WHEN due_in_date IS NOT NULL AND baseline_create_date IS NOT NULL
            THEN DATE_DIFF('day', 
                DATE_PARSE(baseline_create_date, '%Y/%m/%d'),
                DATE_PARSE(due_in_date, '%Y/%m/%d')
            )
            ELSE NULL
        END AS days_to_due,
        
        -- Days from invoice to payment (DSO) - App DB doesn't track clear_date yet
        CAST(NULL AS INTEGER) AS days_to_clear,
        
        -- Overdue flag
        CASE 
            WHEN is_open = TRUE 
                 AND due_in_date IS NOT NULL
                 AND CURRENT_DATE > DATE_PARSE(due_in_date, '%Y/%m/%d')
            THEN TRUE
            ELSE FALSE
        END AS is_overdue
        
    FROM {{ ref('stg_app_ar_invoices') }}
),

-- UNION both sources
unified AS (
    SELECT * FROM kaggle_invoices
    UNION ALL
    SELECT * FROM app_db_invoices
),

-- Add ML-ready features
ml_features AS (
    SELECT
        -- ===== IDENTIFIERS =====
        invoice_id,
        business_code,
        cust_number,
        data_source,
        
        -- ===== RAW DATES (for time-series analysis) =====
        baseline_create_date AS invoice_date_str,
        due_in_date AS due_date_str,
        clear_date AS clear_date_str,
        
        -- Parsed dates
        DATE_PARSE(baseline_create_date, '%Y/%m/%d') AS invoice_date,
        DATE_PARSE(due_in_date, '%Y/%m/%d') AS due_date,
        CASE 
            WHEN clear_date IS NOT NULL AND clear_date != ''
            THEN DATE_PARSE(clear_date, '%Y/%m/%d')
            ELSE NULL
        END AS clear_date,
        
        -- ===== AMOUNT FEATURES =====
        total_open_amount AS invoice_amount_vnd,
        
        -- Amount buckets (categorical feature)
        CASE 
            WHEN total_open_amount >= 100000000 THEN 'LARGE'     -- >= 100M VND
            WHEN total_open_amount >= 50000000 THEN 'MEDIUM'     -- 50-100M
            WHEN total_open_amount >= 10000000 THEN 'SMALL'      -- 10-50M
            ELSE 'MICRO'                                          -- < 10M
        END AS amount_category,
        
        -- ===== TIME FEATURES =====
        days_to_due,
        days_to_clear,  -- This is the TARGET for payment prediction (NULL if unpaid)
        
        -- Overdue buckets
        CASE 
            WHEN days_to_clear IS NOT NULL THEN 'PAID'
            WHEN is_overdue AND DATE_DIFF('day', DATE_PARSE(due_in_date, '%Y/%m/%d'), CURRENT_DATE) > 90 THEN 'OVERDUE_90+'
            WHEN is_overdue AND DATE_DIFF('day', DATE_PARSE(due_in_date, '%Y/%m/%d'), CURRENT_DATE) > 60 THEN 'OVERDUE_60-90'
            WHEN is_overdue AND DATE_DIFF('day', DATE_PARSE(due_in_date, '%Y/%m/%d'), CURRENT_DATE) > 30 THEN 'OVERDUE_30-60'
            WHEN is_overdue THEN 'OVERDUE_0-30'
            ELSE 'CURRENT'
        END AS payment_status_category,
        
        -- ===== PAYMENT TERMS =====
        cust_payment_terms,
        
        -- Extract numeric days from payment terms (e.g., 'NET30' → 30)
        TRY_CAST(
            REGEXP_EXTRACT(cust_payment_terms, '(\d+)', 1)
        AS INTEGER) AS payment_term_days,
        
        -- ===== STATUS FLAGS =====
        is_open,
        is_overdue,
        
        -- ===== LABEL FOR ML (supervised learning) =====
        -- Binary classification: Will pay on time? (1 = yes, 0 = no)
        CASE 
            WHEN days_to_clear IS NOT NULL AND days_to_clear <= days_to_due THEN 1  -- Paid on time
            WHEN days_to_clear IS NOT NULL AND days_to_clear > days_to_due THEN 0   -- Paid late
            ELSE NULL  -- Not paid yet (use for inference only)
        END AS label_paid_on_time,
        
        -- Regression target: Actual days to payment (for DSO prediction)
        days_to_clear AS label_days_to_payment,
        
        -- ===== METADATA =====
        invoice_currency,
        ingested_at,
        CURRENT_TIMESTAMP AS feature_generated_at
        
    FROM unified
)

SELECT * FROM ml_features

-- Filter: Only include records with valid amounts and dates
WHERE invoice_amount_vnd > 0
  AND invoice_date IS NOT NULL
  AND due_date IS NOT NULL
