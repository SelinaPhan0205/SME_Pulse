{{ config(
    materialized = 'table',
    tags = ['gold', 'dimension', 'scd0']
) }}

-- =====================================================================
-- 🚚 DIM_CARRIER: Shipping carrier dimension (SCD Type 0)
-- Purpose: Shipping carrier mapping from seed data
-- Grain: 1 row = 1 carrier
-- =====================================================================

SELECT DISTINCT
  -- Surrogate Key = Natural Key
  carrier_code AS carrier_key,
  
  -- Attributes
  carrier_name_vi,
  service_level,
  
  -- Derived
  CASE
    WHEN service_level = 'SameDay' THEN 1
    WHEN service_level = 'Express' THEN 2
    WHEN service_level = 'Standard' THEN 5
    WHEN service_level = 'Economy' THEN 10
    ELSE 7
  END AS standard_delivery_days,
  
  CASE
    WHEN service_level IN ('SameDay', 'Express') THEN TRUE ELSE FALSE
  END AS is_fast_delivery,
  
  -- Audit
  CURRENT_TIMESTAMP AS created_at
  
FROM {{ ref('seed_carrier_map') }}


