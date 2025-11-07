{{ config(
    materialized='incremental',
    unique_key=['customer_key', 'effective_from'],
    on_schema_change='sync_all_columns',
    tags=['gold', 'dimension', 'ar_dimension', 'production']
) }}

-- =====================================================================
-- 👥 DIM_AR_CUSTOMER: AR Customer Dimension with SCD Type 2
-- Purpose: Customer master data with payment behavior history
-- Grain: 1 row per customer per time period (slowly changing)
-- =====================================================================

WITH customer_data AS (
  SELECT
    -- ===== NATURAL KEY =====
    i.cust_number AS customer_number,
    
    -- ===== BUSINESS ATTRIBUTES (take first value) =====
    MAX(i.business_code) AS business_code,
    MAX(i.invoice_currency) AS primary_currency,
    MAX(i.cust_payment_terms) AS payment_terms,
    
    -- ===== CUSTOMER METRICS =====
    COUNT(DISTINCT i.invoice_id) AS lifetime_invoices,
    COUNT(DISTINCT CASE WHEN i.is_open = false THEN i.invoice_id END) AS paid_invoices,
    COUNT(DISTINCT CASE WHEN i.is_open = true THEN i.invoice_id END) AS open_invoices,
    
    SUM(i.total_open_amount) AS lifetime_total_amount,
    SUM(CASE WHEN i.is_open = false THEN i.total_open_amount ELSE 0 END) AS lifetime_paid_amount,
    SUM(CASE WHEN i.is_open = true THEN i.total_open_amount ELSE 0 END) AS lifetime_open_amount,
    
    -- Payment reliability
    ROUND(
      100.0 * COUNT(DISTINCT CASE WHEN i.is_open = false THEN i.invoice_id END) 
           / NULLIF(COUNT(DISTINCT i.invoice_id), 0),
      2
    ) AS payment_completion_rate_pct,
    
    -- Average DSO (Days to pay)
    COALESCE(ROUND(
      AVG(CASE 
        WHEN i.clear_date IS NOT NULL
        THEN DATE_DIFF('day', 
          DATE_PARSE(i.baseline_create_date, '%Y/%m/%d'),
          DATE_PARSE(i.clear_date, '%Y/%m/%d')
        )
        ELSE NULL
      END),
      2
    ), 0) AS avg_days_to_pay,
    
    -- Overdue history
    SUM(CASE WHEN i.is_open = false AND DATE_DIFF('day', DATE_PARSE(i.baseline_create_date, '%Y/%m/%d'), DATE_PARSE(i.clear_date, '%Y/%m/%d')) > 30 THEN 1 ELSE 0 END) AS overdue_30_count,
    SUM(CASE WHEN i.is_open = false AND DATE_DIFF('day', DATE_PARSE(i.baseline_create_date, '%Y/%m/%d'), DATE_PARSE(i.clear_date, '%Y/%m/%d')) > 60 THEN 1 ELSE 0 END) AS overdue_60_count,
    
    -- ===== TIME TRACKING =====
    MAX(i.ingested_at) AS last_update_date,
    MIN(DATE_PARSE(i.baseline_create_date, '%Y/%m/%d')) AS first_invoice_date,
    MAX(DATE_PARSE(i.baseline_create_date, '%Y/%m/%d')) AS last_invoice_date,
    
    -- ===== CUSTOMER CLASSIFICATION (based on current status) =====
    CASE 
      WHEN SUM(CASE WHEN i.is_open = true AND DATE_DIFF('day', DATE_PARSE(i.due_in_date, '%Y/%m/%d'), CURRENT_DATE) > 90 THEN 1 ELSE 0 END) > 0
      THEN 'HIGH_RISK'
      WHEN SUM(CASE WHEN i.is_open = true AND DATE_DIFF('day', DATE_PARSE(i.due_in_date, '%Y/%m/%d'), CURRENT_DATE) > 30 THEN 1 ELSE 0 END) > 0
      THEN 'AT_RISK'
      WHEN SUM(CASE WHEN i.is_open = false THEN 1 ELSE 0 END) > 0
      THEN 'RELIABLE'
      ELSE 'NEW'
    END AS customer_risk_segment
    
  FROM {{ ref('stg_ar_invoices_vn') }} i
  GROUP BY i.cust_number
),

-- ===== SCD TYPE 2: Create version history =====
scd_logic AS (
  SELECT
    cd.*,
    
    -- Generate surrogate key for this version
    ROW_NUMBER() OVER (PARTITION BY customer_number ORDER BY last_update_date) AS version_num,
    
    -- Effective date for this version
    last_update_date AS effective_from,
    
    -- Is this the current version?
    CASE 
      WHEN LEAD(last_update_date) OVER (PARTITION BY customer_number ORDER BY last_update_date) IS NULL 
      THEN TRUE 
      ELSE FALSE 
    END AS is_current
    
  FROM customer_data cd
)

SELECT
  -- ===== SURROGATE KEY =====
  {{ dbt_utils.generate_surrogate_key(['customer_number', 'effective_from']) }} AS customer_key,
  
  -- ===== NATURAL KEY =====
  customer_number,
  
  -- ===== BUSINESS ATTRIBUTES =====
  business_code,
  primary_currency,
  payment_terms,
  
  -- ===== CUSTOMER CLASSIFICATION =====
  customer_risk_segment,
  
  -- ===== METRICS =====
  lifetime_invoices,
  paid_invoices,
  open_invoices,
  lifetime_total_amount,
  lifetime_paid_amount,
  lifetime_open_amount,
  payment_completion_rate_pct,
  avg_days_to_pay,
  overdue_30_count,
  overdue_60_count,
  
  -- ===== DATES =====
  first_invoice_date,
  last_invoice_date,
  
  -- ===== SCD TYPE 2 =====
  version_num,
  effective_from,
  is_current,
  
  -- ===== AUDIT =====
  CURRENT_TIMESTAMP AS dimension_created_at,
  'AR_CUSTOMER' AS dimension_source

FROM scd_logic

{% if is_incremental() %}
  WHERE effective_from > (SELECT COALESCE(MAX(effective_from), CAST('1900-01-01' AS TIMESTAMP)) FROM {{ this }} WHERE is_current = true)
{% endif %}
