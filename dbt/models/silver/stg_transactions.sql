/*
 * ===================================================
 * Model: stg_transactions (Silver Layer - Staging)
 * ===================================================
 * Mục đích: 
 *   - Làm sạch và chuẩn hóa dữ liệu từ raw.transactions_raw
 *   - Chỉ lấy domain='order' (đơn hàng)
 *   - Parse JSON payload thành các cột riêng biệt
 *   - Incremental load dựa trên updated_at watermark
 * 
 * Input: raw.transactions_raw
 * Output: silver.stg_transactions
 * Strategy: Incremental (merge)
 * ===================================================
 */

{{
  config(
    materialized='incremental',
    unique_key='event_id',
    on_schema_change='append_new_columns'
  )
}}

WITH raw_orders AS (
  SELECT
    -- Metadata columns
    id,
    event_id,
    source,
    domain,
    org_id,
    updated_at,
    ingested_at,
    hash,
    
    -- Parse JSON payload thành các cột
    payload_json->>'order_id' AS order_id,
    (payload_json->>'order_ts')::timestamptz AS order_ts,
    (payload_json->>'subtotal')::numeric AS subtotal,
    (payload_json->>'discount')::numeric AS discount,
    (payload_json->>'shipping_fee')::numeric AS shipping_fee,
    (payload_json->>'tax')::numeric AS tax,
    (payload_json->>'total')::numeric AS total,
    payload_json->>'currency' AS currency,
    payload_json->>'customer_id' AS customer_id,
    payload_json->>'payment_method' AS payment_method,
    payload_json->>'status' AS status
    
  FROM {{ source('raw', 'transactions_raw') }}
  
  WHERE domain = 'order'  -- Chỉ lấy đơn hàng
    AND payload_json IS NOT NULL
  
  {% if is_incremental() %}
    -- Incremental logic: chỉ lấy records mới hơn max(updated_at)
    AND updated_at > (SELECT MAX(updated_at) FROM {{ this }})
  {% endif %}
)

SELECT
  -- Primary key
  event_id,
  
  -- Business keys
  order_id,
  customer_id,
  org_id,
  
  -- Timestamps
  order_ts,
  updated_at,
  ingested_at,
  
  -- Financial metrics (VND)
  subtotal,
  discount,
  shipping_fee,
  tax,
  total,
  currency,
  
  -- Categorical
  payment_method,
  status,
  source,
  
  -- Technical
  hash,
  
  -- Calculated fields
  subtotal - discount AS net_subtotal,
  total - tax AS total_before_tax,
  
  -- Audit
  NOW() AS dbt_updated_at

FROM raw_orders

-- Data quality filters
WHERE total > 0
  AND order_ts IS NOT NULL
  AND order_id IS NOT NULL
