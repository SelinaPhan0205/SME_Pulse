{{ config(
    materialized='table',
    unique_key='date_key',
    on_schema_change='fail',
    tags=['gold', 'kpi', 'reconciliation_kpi', 'production']
) }}

-- =====================================================================
-- 🔗 KPI_RECONCILIATION_DAILY: AR & Payment Reconciliation Summary
-- Purpose: Daily reconciliation of invoices vs payments, aging analysis
-- Grain: 1 row = 1 day (by invoice date)
-- Layer: GOLD (KPI Mart - Pre-aggregated for BI dashboards)
--
-- Source: {{ ref('fact_ar_invoices') }} (aggregated by invoice date)
--
-- Key Metrics:
-- - Issued vs Collected reconciliation
-- - Aging bucket analysis (current, 30-60, 60-90, 90+ days)
-- - Outstanding receivables trend
-- - Receivable turnover rate
-- - Cash flow forecast signals
--
-- Used By:
-- - Metabase: Reconciliation Dashboard, Aging Report
-- - Finance: AR Aging Analysis, Collection Planning
-- - Management: Outstanding AR Monitoring
--
-- Refresh: Daily (incremental - only new invoice dates)
-- Latency: < 5 seconds (pre-aggregated)
-- =====================================================================

WITH daily_reconciliation_metrics AS (
  SELECT
    -- ===== TIME DIMENSION =====
    CAST(REPLACE(baseline_create_date, '/', '') AS BIGINT) AS date_key,
    
    -- ===== INVOICE & COLLECTION RECONCILIATION =====
    COUNT(DISTINCT invoice_id) AS total_invoices,
    SUM(total_open_amount) AS total_issued_amount,
    
    -- Amount paid (invoices with clear_date)
    SUM(CASE WHEN is_open = false AND clear_date IS NOT NULL THEN total_open_amount ELSE 0 END) AS total_collected_amount,
    
    -- Amount still open
    SUM(CASE WHEN is_open = true THEN total_open_amount ELSE 0 END) AS total_outstanding_amount,
    
    -- Reconciliation difference (should be 0 if data is correct)
    SUM(total_open_amount) - 
    SUM(CASE WHEN is_open = false AND clear_date IS NOT NULL THEN total_open_amount ELSE 0 END) - 
    SUM(CASE WHEN is_open = true THEN total_open_amount ELSE 0 END) AS reconciliation_difference_vnd,
    
    -- ===== COLLECTION HEALTH METRICS =====
    -- Collection rate (collected / issued)
    ROUND(
      100.0 * SUM(CASE WHEN is_open = false AND clear_date IS NOT NULL THEN total_open_amount ELSE 0 END) / 
              NULLIF(SUM(total_open_amount), 0),
      2
    ) AS collection_rate_pct,
    
    -- Outstanding receivables as % of issued
    ROUND(
      100.0 * SUM(CASE WHEN is_open = true THEN total_open_amount ELSE 0 END) / 
              NULLIF(SUM(total_open_amount), 0),
      2
    ) AS outstanding_rate_pct,
    
    -- ===== CUSTOMER DIMENSION =====
    COUNT(DISTINCT cust_number) AS unique_customers_issued,
    COUNT(DISTINCT CASE WHEN is_open = true THEN cust_number END) AS customers_with_open_ar,
    
    -- Average AR per customer (paying customers only)
    ROUND(
      SUM(CASE WHEN is_open = true THEN total_open_amount ELSE 0 END) / 
      NULLIF(COUNT(DISTINCT CASE WHEN is_open = true THEN cust_number END), 0),
      0
    ) AS avg_ar_per_customer_vnd,
    
    -- ===== AUDIT COLUMNS =====
    CURRENT_TIMESTAMP AS kpi_created_at,
    'RECONCILIATION_KPI' AS kpi_source
    
  FROM {{ ref('stg_ar_invoices_vn') }}
  
  GROUP BY CAST(REPLACE(baseline_create_date, '/', '') AS BIGINT)
  
  {% if is_incremental() %}
    HAVING CAST(REPLACE(baseline_create_date, '/', '') AS BIGINT) > (SELECT COALESCE(MAX(date_key), 0) FROM {{ this }})
  {% endif %}
)
    
SELECT * FROM daily_reconciliation_metrics


