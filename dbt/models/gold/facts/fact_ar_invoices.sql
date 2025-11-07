{{ config(
    materialized='incremental',
    unique_key='invoice_key',
    on_schema_change='sync_all_columns',
    indexes=[
        {'columns': ['date_key_invoice'], 'type': 'btree'},
        {'columns': ['customer_key'], 'type': 'btree'},
        {'columns': ['is_high_risk'], 'type': 'btree'},
    ],
    tags=['gold', 'fact', 'ar_invoices', 'finance', 'production']
) }}

-- =====================================================================
-- 💵 FACT_AR_INVOICES: Accounts Receivable Invoice transactions
-- Purpose: AR invoice facts for DSO, overdue, and payment analysis
-- Grain: 1 row = 1 AR invoice record
-- =====================================================================

WITH ar_invoices_enriched AS (
  SELECT
    -- ===== SURROGATE KEY (for fact table uniqueness) =====
    {{ dbt_utils.generate_surrogate_key(['i.invoice_id', 'i.baseline_create_date']) }} AS invoice_key,
    
    -- ===== NATURAL KEY =====
    i.invoice_id,
    
    -- ===== DATE DIMENSION FOREIGN KEYS (YYYYMMDD format) =====
    CAST(REPLACE(i.baseline_create_date, '/', '') AS BIGINT) AS date_key_invoice,  -- Invoice creation date
    CAST(REPLACE(i.due_in_date, '/', '') AS BIGINT) AS date_key_due,               -- Payment due date
    CAST(REPLACE(i.clear_date, '/', '') AS BIGINT) AS date_key_clear,              -- Payment cleared date (NULL if open)
    
    -- ===== DIMENSION FOREIGN KEYS =====
    {{ dbt_utils.generate_surrogate_key(['i.cust_number']) }} AS customer_key,
    {{ dbt_utils.generate_surrogate_key(['i.business_code']) }} AS business_key,
    COALESCE(i.invoice_currency, 'USD') AS currency_key,
    
    -- ===== DEGENERATE DIMENSIONS (context, not normalized) =====
    i.cust_number AS customer_number,
    i.business_code,
    i.invoice_currency,
    i.cust_payment_terms AS payment_terms,
    
    -- ===== DATE DIMENSIONS (denormalized for BI) =====
    i.baseline_create_date,
    i.due_in_date,
    i.clear_date,
    
    -- ===== ADDITIVE MEASURES (safe for SUM aggregation) =====
    i.total_open_amount AS invoice_amount_vnd,  -- Primary measure
    
    -- ===== SEMI-ADDITIVE MEASURES (only sum by time dimension carefully) =====
    CASE 
      WHEN i.is_open = true THEN i.total_open_amount
      ELSE 0
    END AS open_amount_vnd,
    
    CASE 
      WHEN i.is_open = false THEN i.total_open_amount
      ELSE 0
    END AS paid_amount_vnd,
    
    -- ===== INVOICE STATUS FLAGS =====
    CASE 
      WHEN i.is_open = true AND i.clear_date IS NULL 
      THEN 'OPEN'
      WHEN i.is_open = false OR i.clear_date IS NOT NULL
      THEN 'CLOSED'
      ELSE 'UNKNOWN'
    END AS invoice_status,
    
    i.is_open AS is_open_flag,
    
    -- ===== OVERDUE & RISK FLAGS (for BI filtering) =====
    CASE 
      WHEN i.is_open = true 
           AND CURRENT_DATE > DATE_PARSE(i.due_in_date, '%Y/%m/%d')
      THEN TRUE
      ELSE FALSE
    END AS is_overdue,
    
    CASE 
      WHEN i.is_open = true 
           AND DATE_DIFF('day', DATE_PARSE(i.due_in_date, '%Y/%m/%d'), CURRENT_DATE) > 30
      THEN TRUE
      ELSE FALSE
    END AS is_overdue_30,
    
    CASE 
      WHEN i.is_open = true 
           AND DATE_DIFF('day', DATE_PARSE(i.due_in_date, '%Y/%m/%d'), CURRENT_DATE) > 60
      THEN TRUE
      ELSE FALSE
    END AS is_overdue_60,
    
    CASE 
      WHEN i.is_open = true 
           AND DATE_DIFF('day', DATE_PARSE(i.due_in_date, '%Y/%m/%d'), CURRENT_DATE) > 90
      THEN TRUE
      ELSE FALSE
    END AS is_high_risk,
    
    -- ===== DERIVED METRICS (for BI segmentation) =====
    CASE 
      WHEN i.total_open_amount > 100000000 THEN 'HIGH_VALUE'
      WHEN i.total_open_amount > 50000000 THEN 'MEDIUM_VALUE'
      ELSE 'LOW_VALUE'
    END AS invoice_value_category,
    
    -- ===== PREDICTABLE COLUMNS (for ML model validation) =====
    -- Days from invoice creation to due date (DSO component)
    DATE_DIFF('day', 
      DATE_PARSE(i.baseline_create_date, '%Y/%m/%d'),
      DATE_PARSE(i.due_in_date, '%Y/%m/%d')
    ) AS days_to_due,
    
    -- Days from invoice creation to payment (Days Sales Outstanding = DSO)
    CASE 
      WHEN i.clear_date IS NOT NULL AND i.clear_date != ''
      THEN DATE_DIFF('day', 
        DATE_PARSE(i.baseline_create_date, '%Y/%m/%d'),
        DATE_PARSE(i.clear_date, '%Y/%m/%d')
      )
      ELSE NULL
    END AS days_to_clear,
    
    -- Current aging (for open invoices)
    CASE 
      WHEN i.is_open = true
      THEN DATE_DIFF('day', DATE_PARSE(i.due_in_date, '%Y/%m/%d'), CURRENT_DATE)
      ELSE NULL
    END AS days_overdue,
    
    -- ===== AUDIT COLUMNS =====
    i.ingested_at,
    CURRENT_TIMESTAMP AS fact_created_at,
    'AR_INVOICES' AS source_system,
    CURRENT_DATE AS fact_date
    
  FROM {{ ref('stg_ar_invoices_vn') }} i
  
  {% if is_incremental() %}
    -- Only load new/updated invoices
    WHERE i.ingested_at > (SELECT MAX(fact_created_at) FROM {{ this }})
  {% endif %}
)

SELECT * FROM ar_invoices_enriched
