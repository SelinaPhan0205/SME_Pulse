{{ config(
    materialized = 'table',
    tags = ['gold', 'fact', 'shipments', 'logistics']
) }}

-- =====================================================================
-- 📦 FACT_SHIPMENTS: Shipping/delivery transactions
-- Purpose: Logistics data from stg_shipments_vn
-- Grain: 1 row = 1 shipment
-- =====================================================================

WITH shipments_enriched AS (
  SELECT
    -- Natural Key
    s.shipment_id_nat AS shipment_id,
    s.order_id,  -- Link to payment
    
    -- Date dimension FK
    CAST(date_format(s.order_date, '%Y%m%d') AS BIGINT) AS date_key,
    s.order_date,
    s.order_time,
    
    -- Dimension FKs
    {{ dbt_utils.generate_surrogate_key(['s.customer_id']) }} AS customer_key,
    COALESCE(s.carrier_code, 'OTHER') AS carrier_key,
    -- Location key: stg_shipments_vn chỉ có delivery_province + delivery_district (không có code)
    -- Để NULL, join sau qua tên province + district
    CAST(NULL AS VARCHAR) AS location_key,
    
    -- Degenerate dimensions
    s.email_norm AS customer_email,
    s.shipping_method_src,
    s.delivery_status_std,
    s.order_status_src,
    s.service_level,
    
    -- Measures
    s.order_value_vnd,
    s.estimated_delivery_days,
    
    -- Geography
    s.delivery_province,
    s.delivery_district,
    s.delivery_region,
    s.shipping_zone,
    
    -- Product context
    s.product_category,
    s.product_brand,
    s.product_type,
    s.products,
    
    -- Customer satisfaction
    s.ratings,
    s.feedback,
    s.delivery_satisfaction_level,
    
    -- Flags
    s.is_priority_shipping,
    CASE WHEN s.delivery_status_std = 'DELIVERED' THEN TRUE ELSE FALSE END AS is_delivered,
    CASE WHEN s.delivery_status_std = 'CANCELLED' THEN TRUE ELSE FALSE END AS is_cancelled,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at
    
  FROM {{ ref('stg_shipments_vn') }} s
)

SELECT * FROM shipments_enriched


