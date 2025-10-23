/*
 * ===================================================
 * Model: fact_orders (Gold Layer - Fact Table)
 * ===================================================
 * Mục đích:
 *   - Tổng hợp doanh thu theo ngày, tổ chức
 *   - Tính các metrics: revenue, orders count, avg order value
 *   - Phục vụ cho dashboard và reporting
 * 
 * Input: silver.stg_transactions
 * Output: gold.fact_orders
 * Strategy: Table (full refresh)
 * Grain: 1 row = 1 ngày x 1 org x 1 payment_method
 * ===================================================
 */

{{
  config(
    materialized='table',
    schema='gold',
    format='PARQUET'
  )
}}

WITH daily_orders AS (
  SELECT
    -- Dimensions
    DATE(order_ts) AS order_date,
    org_id,
    payment_method,
    currency,
    
    -- Metrics: Counts
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_id) AS unique_customers,
    
    -- Metrics: Revenue (VND)
    SUM(subtotal) AS gross_revenue,
    SUM(discount) AS total_discount,
    SUM(net_subtotal) AS net_revenue,
    SUM(shipping_fee) AS total_shipping_fee,
    SUM(tax) AS total_tax,
    SUM(total) AS total_revenue,
    
    -- Metrics: Averages
    AVG(total) AS avg_order_value,
    AVG(subtotal) AS avg_subtotal,
    
    -- Metrics: Min/Max
    MIN(total) AS min_order_value,
    MAX(total) AS max_order_value,
    
    -- Audit
    MAX(updated_at) AS last_updated_at
    
  FROM {{ ref('stg_transactions') }}
  
  WHERE status = 'completed'  -- Chỉ tính đơn hoàn thành
    AND total > 0
  
  GROUP BY 1, 2, 3, 4
)

SELECT
  -- Generate surrogate key (MD5 hash) - Trino syntax
  TO_HEX(MD5(TO_UTF8(CAST(order_date AS VARCHAR) || org_id || payment_method))) AS fact_key,
  
  -- Dimensions
  order_date,
  org_id,
  payment_method,
  currency,
  
  -- Metrics
  total_orders,
  unique_customers,
  gross_revenue,
  total_discount,
  net_revenue,
  total_shipping_fee,
  total_tax,
  total_revenue,
  avg_order_value,
  avg_subtotal,
  min_order_value,
  max_order_value,
  
  -- Calculated KPIs
  ROUND((CAST(total_discount AS DOUBLE) / NULLIF(gross_revenue, 0)) * 100, 2) AS discount_rate_pct,
  ROUND((CAST(net_revenue AS DOUBLE) / NULLIF(total_orders, 0)), 0) AS revenue_per_order,
  
  -- Audit
  last_updated_at,
  CURRENT_TIMESTAMP AS dbt_created_at

FROM daily_orders

ORDER BY order_date DESC, org_id, payment_method
