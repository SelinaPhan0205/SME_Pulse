{{ config(
    materialized='table',
    unique_key='date_key',
    on_schema_change='sync_all_columns',
    tags=['gold', 'kpi', 'revenue_kpi', 'production']
) }}

-- =====================================================================
-- 💰 KPI_DAILY_REVENUE: Daily Revenue & Invoice Volume Metrics
-- Purpose: Daily invoice issuance, amount tracking, and revenue trends
-- Grain: 1 row = 1 day (by invoice creation date)
-- Layer: GOLD (KPI Mart - Pre-aggregated for BI dashboards)
--
-- Source: {{ ref('stg_ar_invoices_vn') }} (Silver - clean baseline data)
--
-- Key Metrics:
-- - Daily invoice volume & amounts issued
-- - Payment status breakdown
-- - Revenue recognition trends
-- - Customer/business unit distribution
--
-- Used By:
-- - Metabase: Revenue Dashboard, Daily Trend
-- - Finance: Revenue Recognition, Forecasting
-- - Management: Invoice Volume Monitoring
--
-- Refresh: Daily (incremental - only new dates)
-- Latency: < 5 seconds (pre-aggregated)
-- =====================================================================

WITH daily_revenue_metrics AS (
  SELECT
    -- ===== TIME DIMENSION (from Silver baseline_create_date) =====
    CAST(REPLACE(baseline_create_date, '/', '') AS BIGINT) AS date_key,
    
    -- ===== INVOICE COUNT METRICS =====
    COUNT(DISTINCT invoice_id) AS invoices_issued,
    
    -- Status breakdown
    SUM(CASE WHEN is_open = true THEN 1 ELSE 0 END) AS invoices_open,
    SUM(CASE WHEN is_open = false THEN 1 ELSE 0 END) AS invoices_paid,
    
    -- ===== REVENUE METRICS (Amount-based) =====
    SUM(total_open_amount) AS total_revenue_issued,
    
    -- Breakdown by payment status
    SUM(CASE WHEN is_open = false THEN total_open_amount ELSE 0 END) AS total_paid_amount,
    SUM(CASE WHEN is_open = true THEN total_open_amount ELSE 0 END) AS total_open_receivables,
    
    -- ===== CUSTOMER SEGMENTATION =====
    COUNT(DISTINCT cust_number) AS unique_customers,
    COUNT(DISTINCT business_code) AS business_units,
    
    -- ===== KPI RATES (%) =====
    ROUND(
      100.0 * SUM(CASE WHEN is_open = false THEN 1 ELSE 0 END) / 
              NULLIF(COUNT(DISTINCT invoice_id), 0),
      2
    ) AS payment_completion_rate_pct,
    
    -- Cash conversion ratio (paid vs issued)
    ROUND(
      100.0 * SUM(CASE WHEN is_open = false THEN total_open_amount ELSE 0 END) / 
              NULLIF(SUM(total_open_amount), 0),
      2
    ) AS cash_conversion_rate_pct,
    
    -- Average invoice value
    ROUND(
      SUM(total_open_amount) / NULLIF(COUNT(DISTINCT invoice_id), 0),
      0
    ) AS avg_invoice_value_vnd,
    
    -- ===== AUDIT COLUMNS =====
    CURRENT_TIMESTAMP AS kpi_created_at,
    'DAILY_REVENUE_KPI' AS kpi_source
    
  FROM {{ ref('stg_ar_invoices_vn') }}
  
  GROUP BY CAST(REPLACE(baseline_create_date, '/', '') AS BIGINT)
  
  {% if is_incremental() %}
    HAVING CAST(REPLACE(baseline_create_date, '/', '') AS BIGINT) > (SELECT COALESCE(MAX(date_key), 0) FROM {{ this }})
  {% endif %}
)

SELECT * FROM daily_revenue_metrics


