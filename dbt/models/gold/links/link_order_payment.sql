{{ config(
    materialized = 'incremental',
    unique_key = 'match_key',
    incremental_strategy = 'merge',
    tags = ['gold', 'link', 'reconciliation', 'cross_channel']
) }}

-- =====================================================================
-- 🔗 LINK_ORDER_PAYMENT: Wholesale Orders ↔ Retail Payments
-- Purpose: Cross-channel reconciliation (orders from wholesale vs retail payments)
-- Grain: 1 row = 1 order-payment match (bijective: 1 order ↔ 1 payment)
-- Fixes applied:
--   [P0] Removed 1% sampling (MOD hack)
--   [P1] Enforced bijective matching to prevent double-counting
--   [P1] Added incremental strategy for performance at scale
-- =====================================================================

WITH wholesale_orders AS (
  SELECT
    order_id,
    date_key,
    order_date,
    customer_key,
    product_key,
    channel_key,
    quantity,
    revenue AS order_revenue_vnd,
    gross_profit
  FROM {{ ref('fact_orders') }}
  WHERE channel_key != 'Online'
    {% if is_incremental() %}
    AND order_date >= (SELECT COALESCE(MAX(order_date), DATE '2020-01-01') FROM {{ this }}) - INTERVAL '7' DAY
    {% endif %}
),

retail_payments AS (
  SELECT
    payment_id,
    date_key,
    payment_date,
    customer_key,
    product_key,
    payment_method_key,
    total_amount_vnd AS payment_amount_vnd,
    is_successful_payment
  FROM {{ ref('fact_payments') }}
  WHERE is_successful_payment = TRUE
    {% if is_incremental() %}
    AND payment_date >= (SELECT COALESCE(MAX(payment_date), DATE '2020-01-01') FROM {{ this }}) - INTERVAL '7' DAY
    {% endif %}
),

-- Match on: customer + product + date proximity + amount similarity
potential_matches AS (
  SELECT
    o.order_id,
    o.order_date,
    o.customer_key,
    o.product_key,
    o.order_revenue_vnd,
    
    p.payment_id,
    p.payment_date,
    p.payment_amount_vnd,
    
    -- Match criteria
    -- 1. Customer match (exact)
    CASE WHEN o.customer_key = p.customer_key THEN 50 ELSE 0 END AS customer_match_score,
    
    -- 2. Product match (exact)
    CASE WHEN o.product_key = p.product_key THEN 30 ELSE 0 END AS product_match_score,
    
    -- 3. Date proximity (within 30 days)
    ABS(DATE_DIFF('day', o.order_date, p.payment_date)) AS date_diff_days,
    CASE 
      WHEN ABS(DATE_DIFF('day', o.order_date, p.payment_date)) <= 3 THEN 20
      WHEN ABS(DATE_DIFF('day', o.order_date, p.payment_date)) <= 7 THEN 15
      WHEN ABS(DATE_DIFF('day', o.order_date, p.payment_date)) <= 30 THEN 10
      ELSE 0
    END AS date_match_score,
    
    -- 4. Amount similarity (order revenue vs payment amount)
    ABS(o.order_revenue_vnd - p.payment_amount_vnd) AS amount_variance_vnd,
    o.order_revenue_vnd - p.payment_amount_vnd AS amount_diff_vnd,
    
    CURRENT_TIMESTAMP AS created_at
    
  FROM wholesale_orders o
  INNER JOIN retail_payments p
    ON o.customer_key = p.customer_key  -- Must match customer
    AND o.product_key = p.product_key   -- Must match product
    AND ABS(DATE_DIFF('day', o.order_date, p.payment_date)) <= 30  -- Within 30 days
),

scored_matches AS (
  SELECT
    *,
    customer_match_score + product_match_score + date_match_score AS total_match_score,
    
    CASE 
      WHEN customer_match_score + product_match_score + date_match_score >= 90 THEN 'HIGH'
      WHEN customer_match_score + product_match_score + date_match_score >= 70 THEN 'MEDIUM'
      WHEN customer_match_score + product_match_score + date_match_score >= 50 THEN 'LOW'
      ELSE 'VERY_LOW'
    END AS match_confidence,
    
    -- Best match per order
    ROW_NUMBER() OVER (
      PARTITION BY order_id 
      ORDER BY (customer_match_score + product_match_score + date_match_score) DESC,
               ABS(amount_diff_vnd) ASC
    ) AS match_rank_per_order,
    
    -- Best match per payment
    ROW_NUMBER() OVER (
      PARTITION BY payment_id 
      ORDER BY (customer_match_score + product_match_score + date_match_score) DESC,
               ABS(amount_diff_vnd) ASC
    ) AS match_rank_per_payment
    
  FROM potential_matches
)

-- FIX: Enforce bijective matching — only keep pairs where BOTH sides are best match
SELECT
  CAST(CAST(order_id AS VARCHAR) || '_' || CAST(payment_id AS VARCHAR) AS VARCHAR) AS match_key,
  order_id,
  order_date,
  customer_key,
  product_key,
  order_revenue_vnd,
  payment_id,
  payment_date,
  payment_amount_vnd,
  amount_variance_vnd,
  amount_diff_vnd,
  date_diff_days,
  customer_match_score,
  product_match_score,
  date_match_score,
  total_match_score,
  match_confidence,
  TRUE AS is_best_match_for_order,
  TRUE AS is_best_match_for_payment,
  created_at
FROM scored_matches
WHERE match_rank_per_order = 1 AND match_rank_per_payment = 1
  AND total_match_score >= 50
ORDER BY order_id, total_match_score DESC

