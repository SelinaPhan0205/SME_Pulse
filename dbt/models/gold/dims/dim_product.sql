{{ config(
    materialized = 'table',
    tags = ['gold', 'dimension', 'scd1']
) }}

-- =====================================================================
-- 📦 DIM_PRODUCT: Product dimension (SCD Type 1)
-- Purpose: Product master data from orders + payments
-- Grain: 1 row = 1 product
-- =====================================================================

WITH product_from_orders AS (
  SELECT DISTINCT
    product_code AS product_id
  FROM {{ ref('stg_orders_vn') }}
  WHERE product_code IS NOT NULL
),

product_from_payments AS (
  -- Payments có product info chi tiết
  SELECT DISTINCT
    products AS product_id,
    product_category,
    product_brand,
    product_type
  FROM {{ ref('stg_payments_vn') }}
  WHERE products IS NOT NULL
),

product_union AS (
  SELECT product_id, NULL AS product_category, NULL AS product_brand, NULL AS product_type
  FROM product_from_orders
  UNION
  SELECT product_id, product_category, product_brand, product_type
  FROM product_from_payments
),

product_consolidated AS (
  SELECT
    product_id,
    MAX(product_category) AS product_category,
    MAX(product_brand) AS product_brand,
    MAX(product_type) AS product_type
  FROM product_union
  GROUP BY product_id
),

product_enriched AS (
  SELECT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(['product_id']) }} AS product_key,
    
    -- Natural Key
    product_id,
    
    -- Attributes
    COALESCE(product_category, 'Unknown') AS product_category,
    COALESCE(product_brand, 'Unknown') AS product_brand,
    COALESCE(product_type, 'Unknown') AS product_type,
    
    -- Derived: Product hierarchy
    CASE
      WHEN LOWER(COALESCE(product_category, '')) LIKE '%electronic%' THEN 'Electronics'
      WHEN LOWER(COALESCE(product_category, '')) LIKE '%clothing%' 
        OR LOWER(COALESCE(product_category, '')) LIKE '%fashion%' THEN 'Fashion'
      WHEN LOWER(COALESCE(product_category, '')) LIKE '%food%' 
        OR LOWER(COALESCE(product_category, '')) LIKE '%grocery%' THEN 'FMCG'
      WHEN LOWER(COALESCE(product_category, '')) LIKE '%home%' 
        OR LOWER(COALESCE(product_category, '')) LIKE '%decor%' THEN 'Home & Living'
      ELSE 'Other'
    END AS product_division,
    
    -- Active flag
    TRUE AS is_active,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
    
  FROM product_consolidated
)

SELECT * FROM product_enriched


