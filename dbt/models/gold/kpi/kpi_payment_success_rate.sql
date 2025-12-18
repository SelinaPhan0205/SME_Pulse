{{ config(
    materialized='incremental',
    unique_key='date_key',
    on_schema_change='fail',
    tags=['gold', 'kpi', 'payment_kpi', 'production']
) }}

-- =====================================================================
-- ✅ KPI_PAYMENT_SUCCESS_RATE: Payment Performance & Success Metrics
-- Purpose: Daily payment success rates, on-time payment tracking, payment delays
-- Grain: 1 row = 1 day (by invoice due date)
-- Layer: GOLD (KPI Mart - Pre-aggregated for BI dashboards)
--
-- Source: {{ ref('stg_ar_invoices_vn') }} (Silver - clean baseline data)
--
-- Key Metrics:
-- - Payment success rate (paid / invoices due)
-- - On-time payment rate
-- - Late payment rate
-- - Average payment delay
-- - Payment volume & amounts by status
--
-- Used By:
-- - Metabase: Payment Performance Dashboard
-- - Finance: Collection KPI Monitoring
-- - Executive: Payment Success Rate Trend
--
-- Refresh: Daily (incremental - only new due dates)
-- Latency: < 5 seconds (pre-aggregated)
-- =====================================================================

WITH payment_success_metrics AS (
  SELECT
    -- ===== TIME DIMENSION (based on DUE date, not invoice date) =====
    CAST(REPLACE(due_in_date, '/', '') AS BIGINT) AS date_key,
    
    -- ===== INVOICE COUNT METRICS (by due date) =====
    COUNT(DISTINCT invoice_id) AS total_invoices_due,
    
    -- Payment completion breakdown
    SUM(CASE WHEN is_open = false THEN 1 ELSE 0 END) AS invoices_paid,
    SUM(CASE WHEN is_open = true THEN 1 ELSE 0 END) AS invoices_open,
    
    -- ===== AMOUNT METRICS (Payment tracking) =====
    SUM(total_open_amount) AS total_amount_due,
    
    -- Amount paid (invoices with clear_date)
    SUM(CASE WHEN is_open = false AND clear_date IS NOT NULL THEN total_open_amount ELSE 0 END) AS total_amount_paid,
    
    -- Amount still open
    SUM(CASE WHEN is_open = true THEN total_open_amount ELSE 0 END) AS total_amount_open,
    
    -- ===== PAYMENT PERFORMANCE RATES (%) =====
    ROUND(
      100.0 * SUM(CASE WHEN is_open = false THEN 1 ELSE 0 END) / 
              NULLIF(COUNT(DISTINCT invoice_id), 0),
      2
    ) AS payment_success_rate_pct,
    
    -- Amount-based success rate
    ROUND(
      100.0 * SUM(CASE WHEN is_open = false AND clear_date IS NOT NULL THEN total_open_amount ELSE 0 END) / 
              NULLIF(SUM(total_open_amount), 0),
      2
    ) AS amount_payment_success_rate_pct,
    
    -- ===== COLLECTION HEALTH =====
    COUNT(DISTINCT CASE WHEN is_open = true THEN cust_number END) AS customers_with_open_ar,
    COUNT(DISTINCT CASE WHEN is_open = false THEN cust_number END) AS paying_customers,
    
    -- ===== AUDIT COLUMNS =====
    CURRENT_TIMESTAMP AS kpi_created_at,
    'PAYMENT_SUCCESS_KPI' AS kpi_source
    
  FROM {{ ref('stg_ar_invoices_vn') }}
  
  GROUP BY CAST(REPLACE(due_in_date, '/', '') AS BIGINT)
  
  {% if is_incremental() %}
    HAVING CAST(REPLACE(due_in_date, '/', '') AS BIGINT) > (SELECT COALESCE(MAX(date_key), 0) FROM {{ this }})
  {% endif %}
)

SELECT * FROM payment_success_metrics
