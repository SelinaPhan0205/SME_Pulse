{{ config(
    materialized='incremental',
    unique_key='date_key',
    on_schema_change='fail',
    tags=['gold', 'kpi', 'ar_kpi', 'production']
) }}

-- =====================================================================
-- 📊 KPI_AR_DSO_ANALYSIS: Days Sales Outstanding & AR Analytics
-- Purpose: Daily DSO, overdue aging, and AR health metrics for BI dashboards
-- Grain: 1 row = 1 day
-- Layer: GOLD (KPI Mart - Pre-aggregated for BI)
--
-- Source: {{ ref('fact_ar_invoices') }} (aggregated)
--
-- Key Metrics:
-- - DSO (Days Sales Outstanding): avg days from invoice to payment
-- - Overdue aging: invoices_overdue_30, invoices_overdue_60, invoices_overdue_90
-- - Open amount tracking: open_amount_vnd, paid_amount_vnd
-- - High-risk alert: high_risk_invoices
--
-- Used By:
-- - Metabase Dashboard: AR Overview, Aging Analysis
-- - Executive Reports: DSO Trend, Overdue Risk
-- - Finance Team: Collection Priority
--
-- Refresh: Daily (after fact_ar_invoices loads)
-- Latency: < 5 seconds (pre-aggregated)
-- =====================================================================

WITH daily_ar_metrics AS (
  SELECT
    -- ===== TIME DIMENSION =====
    date_key_invoice AS date_key,
    
    -- ===== INVOICE COUNT METRICS =====
    COUNT(DISTINCT invoice_id) AS total_invoices,
    
    -- Status breakdown
    SUM(CASE WHEN invoice_status = 'OPEN' THEN 1 ELSE 0 END) AS open_invoices,
    SUM(CASE WHEN invoice_status = 'CLOSED' THEN 1 ELSE 0 END) AS closed_invoices,
    
    -- ===== AMOUNT METRICS (ADDITIVE) =====
    SUM(invoice_amount_vnd) AS total_invoice_amount,
    SUM(open_amount_vnd) AS open_amount_vnd,
    SUM(paid_amount_vnd) AS paid_amount_vnd,
    
    -- ===== OVERDUE METRICS =====
    SUM(CASE WHEN is_overdue THEN 1 ELSE 0 END) AS invoices_overdue,
    SUM(CASE WHEN is_overdue_30 THEN 1 ELSE 0 END) AS invoices_overdue_30,
    SUM(CASE WHEN is_overdue_60 THEN 1 ELSE 0 END) AS invoices_overdue_60,
    SUM(CASE WHEN is_high_risk THEN 1 ELSE 0 END) AS high_risk_invoices,
    
    -- Overdue amount
    SUM(CASE WHEN is_overdue THEN invoice_amount_vnd ELSE 0 END) AS overdue_amount_vnd,
    SUM(CASE WHEN is_overdue_30 THEN invoice_amount_vnd ELSE 0 END) AS overdue_30_amount_vnd,
    SUM(CASE WHEN is_overdue_60 THEN invoice_amount_vnd ELSE 0 END) AS overdue_60_amount_vnd,
    SUM(CASE WHEN is_high_risk THEN invoice_amount_vnd ELSE 0 END) AS high_risk_amount_vnd,
    
    -- ===== DSO METRICS (Days Sales Outstanding) =====
    ROUND(AVG(CASE WHEN days_to_clear IS NOT NULL THEN days_to_clear END), 2) AS avg_dso,
    ROUND(MAX(CASE WHEN days_to_clear IS NOT NULL THEN days_to_clear END), 0) AS max_dso,
    ROUND(MIN(CASE WHEN days_to_clear IS NOT NULL THEN days_to_clear END), 0) AS min_dso,
    
    -- Days overdue for open invoices
    ROUND(AVG(CASE WHEN is_open_flag = true THEN days_overdue ELSE NULL END), 2) AS avg_days_overdue,
    ROUND(MAX(CASE WHEN is_open_flag = true THEN days_overdue ELSE NULL END), 0) AS max_days_overdue,
    
    -- ===== INVOICE VALUE DISTRIBUTION =====
    SUM(CASE WHEN invoice_value_category = 'HIGH_VALUE' THEN 1 ELSE 0 END) AS high_value_count,
    SUM(CASE WHEN invoice_value_category = 'MEDIUM_VALUE' THEN 1 ELSE 0 END) AS medium_value_count,
    SUM(CASE WHEN invoice_value_category = 'LOW_VALUE' THEN 1 ELSE 0 END) AS low_value_count,
    
    SUM(CASE WHEN invoice_value_category = 'HIGH_VALUE' THEN invoice_amount_vnd ELSE 0 END) AS high_value_amount_vnd,
    SUM(CASE WHEN invoice_value_category = 'MEDIUM_VALUE' THEN invoice_amount_vnd ELSE 0 END) AS medium_value_amount_vnd,
    SUM(CASE WHEN invoice_value_category = 'LOW_VALUE' THEN invoice_amount_vnd ELSE 0 END) AS low_value_amount_vnd,
    
    -- ===== KPI RATES (%) =====
    ROUND(
      100.0 * SUM(CASE WHEN invoice_status = 'CLOSED' THEN 1 ELSE 0 END) / COUNT(*),
      2
    ) AS closed_rate_pct,
    
    ROUND(
      100.0 * SUM(CASE WHEN is_overdue THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN is_open_flag THEN 1 ELSE 0 END), 0),
      2
    ) AS overdue_rate_pct,
    
    -- ===== AUDIT COLUMNS =====
    CURRENT_TIMESTAMP AS kpi_created_at,
    'AR_KPI' AS kpi_source
    
  FROM {{ ref('fact_ar_invoices') }}
  
  GROUP BY date_key_invoice
  
  {% if is_incremental() %}
    HAVING date_key_invoice > (SELECT COALESCE(MAX(date_key), 0) FROM {{ this }})
  {% endif %}
)

SELECT * FROM daily_ar_metrics
