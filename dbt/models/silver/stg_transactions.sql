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
    on_schema_change='append_new_columns',
    format='PARQUET',
    partitioning=["DATE(order_ts)"]
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
    
    -- Parse JSON payload thành các cột (Trino JSON functions)
    JSON_EXTRACT_SCALAR(payload_json, '$.order_id') AS order_id,
    CAST(JSON_EXTRACT_SCALAR(payload_json, '$.order_ts') AS TIMESTAMP) AS order_ts,
    CAST(JSON_EXTRACT_SCALAR(payload_json, '$.subtotal') AS DECIMAL(15,2)) AS subtotal,
    CAST(JSON_EXTRACT_SCALAR(payload_json, '$.discount') AS DECIMAL(15,2)) AS discount,
    CAST(JSON_EXTRACT_SCALAR(payload_json, '$.shipping_fee') AS DECIMAL(15,2)) AS shipping_fee,
    CAST(JSON_EXTRACT_SCALAR(payload_json, '$.tax') AS DECIMAL(15,2)) AS tax,
    CAST(JSON_EXTRACT_SCALAR(payload_json, '$.total') AS DECIMAL(15,2)) AS total,
    JSON_EXTRACT_SCALAR(payload_json, '$.currency') AS currency,
    JSON_EXTRACT_SCALAR(payload_json, '$.customer_id') AS customer_id,
    JSON_EXTRACT_SCALAR(payload_json, '$.payment_method') AS payment_method,
    JSON_EXTRACT_SCALAR(payload_json, '$.status') AS status
    
  FROM {{ source('bronze', 'transactions_raw') }}
  
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
  CURRENT_TIMESTAMP AS dbt_updated_at

FROM raw_orders

-- Data quality filters
WHERE total > 0
  AND order_ts IS NOT NULL
  AND order_id IS NOT NULL
