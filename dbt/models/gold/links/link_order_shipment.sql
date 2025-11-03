{{
  config(
    materialized='table',
    schema='gold',
    tags=['gold', 'links', 'reconciliation']
  )
}}

-- depends_on: {{ ref('fact_orders') }}
-- depends_on: {{ ref('fact_shipments') }}
-- depends_on: {{ ref('stg_orders_vn') }}

-- =====================================================================
-- LINK_ORDER_SHIPMENT: Đối soát Orders vs Shipments
-- Match rule: Time window + Customer matching
-- Purpose: Track order fulfillment and delivery
-- =====================================================================

WITH orders AS (
  -- Lấy orders
  SELECT 
    f.order_id,
    f.order_date,
    f.customer_key,
    s.customer_code,
    s.branch_id,
    f.revenue AS order_amount_vnd
  FROM {{ ref('fact_orders') }} f
  JOIN {{ ref('stg_orders_vn') }} s 
    ON f.order_id = s.order_id_nat
  WHERE MOD(f.date_key, 100) = 0  -- SAMPLE 1% for testing
),

shipments AS (
  -- Lấy shipments
  SELECT
    f.shipment_id,
    f.order_date AS ship_date,  -- fact_shipments stores order_date, not ship_date
    f.customer_key,
    f.customer_email AS customer_id,
    f.shipping_method_src AS carrier_code,
    f.order_value_vnd AS shipment_order_value_vnd,
    f.is_delivered,
    f.is_cancelled,
    f.is_priority_shipping,
    f.estimated_delivery_days
  FROM {{ ref('fact_shipments') }} f
  WHERE 
    f.is_cancelled = FALSE  -- Exclude cancelled shipments
    AND MOD(f.date_key, 100) = 0  -- SAMPLE 1% for testing
),

-- Cross join với điều kiện
potential_matches AS (
  SELECT
    o.order_id,
    s.shipment_id,
    o.order_date,
    s.ship_date,
    o.customer_code AS order_customer,
    s.customer_id AS shipment_customer,
    o.branch_id,
    s.carrier_code,
    o.order_amount_vnd,
    s.shipment_order_value_vnd,
    s.is_delivered,
    s.is_priority_shipping,
    s.estimated_delivery_days,
    
    -- Tính toán sự chênh lệch
    ABS(o.order_amount_vnd - s.shipment_order_value_vnd) AS amount_diff_vnd,
    ABS(DATE_DIFF('day', o.order_date, s.ship_date)) AS days_diff,
    
    -- Tỷ lệ chênh lệch
    ABS(o.order_amount_vnd - s.shipment_order_value_vnd) * 1.0 / NULLIF(o.order_amount_vnd, 0) AS amount_diff_pct,
    
    -- Customer match check (optional, may not always have matching customer codes)
    CASE 
      WHEN o.customer_code = s.customer_id THEN TRUE
      ELSE FALSE
    END AS is_customer_match
    
  FROM orders o
  CROSS JOIN shipments s
  WHERE 
    -- Filter 1: Time window <= 7 days (shipment usually happens within a week)
    ABS(DATE_DIFF('day', o.order_date, s.ship_date)) <= 7
    -- Filter 2: Shipment should be AFTER order (or same day)
    AND s.ship_date >= o.order_date
    -- Filter 3: Amount difference <= 20% (shipment may be partial)
    AND ABS(o.order_amount_vnd - s.shipment_order_value_vnd) <= 0.20 * o.order_amount_vnd
),

-- Tính match quality
matched AS (
  SELECT
    order_id,
    shipment_id,
    order_date,
    ship_date,
    order_customer,
    shipment_customer,
    is_customer_match,
    branch_id,
    carrier_code,
    order_amount_vnd,
    shipment_order_value_vnd,
    amount_diff_vnd,
    days_diff,
    amount_diff_pct,
    is_delivered,
    is_priority_shipping,
    estimated_delivery_days,
    
    -- Match rule classification
    CASE
      WHEN is_customer_match AND days_diff <= 1 AND amount_diff_pct <= 0.05 THEN 'exact_match'
      WHEN is_customer_match AND days_diff <= 3 AND amount_diff_pct <= 0.10 THEN 'high_confidence'
      WHEN days_diff <= 3 AND amount_diff_pct <= 0.10 THEN 'medium_confidence_no_customer'
      WHEN days_diff <= 5 AND amount_diff_pct <= 0.15 THEN 'low_confidence'
      ELSE 'very_low_confidence'
    END AS match_rule,
    
    -- Confidence score
    CASE
      WHEN is_customer_match AND days_diff <= 1 AND amount_diff_pct <= 0.05 THEN 0.95
      WHEN is_customer_match AND days_diff <= 2 AND amount_diff_pct <= 0.08 THEN 0.85
      WHEN is_customer_match AND days_diff <= 3 AND amount_diff_pct <= 0.10 THEN 0.75
      WHEN days_diff <= 3 AND amount_diff_pct <= 0.10 THEN 0.65
      WHEN days_diff <= 5 AND amount_diff_pct <= 0.15 THEN 0.50
      ELSE 0.35
    END AS confidence_score,
    
    -- Match quality flags
    days_diff <= 2 AS is_time_match,
    amount_diff_pct <= 0.10 AS is_amount_match,
    
    -- Fulfillment metrics
    CASE 
      WHEN is_delivered THEN 'delivered'
      WHEN NOT is_delivered AND days_diff > estimated_delivery_days THEN 'delayed'
      ELSE 'in_transit'
    END AS fulfillment_status,
    
    -- Link metadata
    'order_shipment_reconciliation' AS link_type,
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
    
  FROM potential_matches
),

-- Deduplicate: 1 order có thể có nhiều shipments (partial shipments)
-- Giữ tất cả high-confidence matches
deduped AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY order_id 
      ORDER BY confidence_score DESC, days_diff ASC, amount_diff_vnd ASC
    ) AS rank_order,
    ROW_NUMBER() OVER (
      PARTITION BY shipment_id 
      ORDER BY confidence_score DESC, days_diff ASC, amount_diff_vnd ASC
    ) AS rank_shipment
  FROM matched
)

-- Kết quả cuối
SELECT
  order_id,
  shipment_id,
  order_date,
  ship_date,
  order_customer,
  shipment_customer,
  is_customer_match,
  branch_id,
  carrier_code,
  order_amount_vnd,
  shipment_order_value_vnd,
  amount_diff_vnd,
  ROUND(amount_diff_pct * 100, 2) AS amount_diff_pct,
  days_diff,
  match_rule,
  ROUND(confidence_score, 3) AS confidence_score,
  is_time_match,
  is_amount_match,
  is_delivered,
  is_priority_shipping,
  estimated_delivery_days,
  fulfillment_status,
  link_type,
  created_at,
  updated_at
FROM deduped
WHERE 
  -- Giữ best match cho mỗi order/shipment
  (rank_order = 1 OR rank_shipment = 1)
  -- HOẶC giữ các high-confidence matches (allow multiple shipments per order)
  OR confidence_score >= 0.75