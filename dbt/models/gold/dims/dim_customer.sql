{{ config(
    materialized = 'table',
    tags = ['gold', 'dimension', 'scd2']
) }}

-- =====================================================================
-- 👤 DIM_CUSTOMER: Customer dimension (SCD Type 2)
-- Purpose: Customer master data from orders + payments
-- Grain: 1 row = 1 customer (current + historical versions)
-- =====================================================================

WITH customer_from_orders AS (
  -- Orders có customer_code (VARCHAR)
  SELECT DISTINCT
    CAST(customer_code AS VARCHAR) AS customer_id,
    CAST(NULL AS VARCHAR) AS email,
    CAST(NULL AS VARCHAR) AS province_name
  FROM {{ ref('stg_orders_vn') }}
  WHERE customer_code IS NOT NULL
),

customer_from_payments AS (
  -- Payments có email + province (customer_id là DOUBLE)
  SELECT DISTINCT
    CAST(customer_id AS VARCHAR) AS customer_id,
    email_norm AS email,
    province_name
  FROM {{ ref('stg_payments_vn') }}
  WHERE customer_id IS NOT NULL
),

customer_union AS (
  SELECT * FROM customer_from_orders
  UNION
  SELECT * FROM customer_from_payments
),

customer_consolidated AS (
  SELECT
    customer_id,
    MAX(email) AS email,
    MAX(province_name) AS province_name
  FROM customer_union
  GROUP BY customer_id
),

customer_enriched AS (
  SELECT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} AS customer_key,
    
    -- Natural Key
    customer_id,
    
    -- Attributes
    email,
    province_name,
    
    -- Derived: Customer segment (based on activity - to be enriched later)
    'STANDARD' AS customer_segment,  -- Placeholder: 'VIP', 'STANDARD', 'NEW', 'INACTIVE'
    
    -- SCD Type 2 attributes
    DATE '2022-01-01' AS valid_from,
    DATE '9999-12-31' AS valid_to,
    TRUE AS is_current,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
    
  FROM customer_consolidated
)

SELECT * FROM customer_enriched
