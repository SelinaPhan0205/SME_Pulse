{{ config(
    materialized = 'table',
    tags = ['gold', 'dimension', 'scd0']
) }}

-- =====================================================================
-- 📺 DIM_CHANNEL: Sales channel dimension (SCD Type 0)
-- Purpose: Sales channel mapping from seed data
-- Grain: 1 row = 1 sales channel
-- =====================================================================

SELECT DISTINCT
  -- Surrogate Key = Natural Key (stable codes)
  channel_code AS channel_key,
  
  -- Attributes
  channel_name_vi,
  
  -- Derived
  CASE
    WHEN channel_code = 'Online' THEN 'Digital'
    WHEN channel_code IN ('CHTT', 'BANLE') THEN 'Physical'
    WHEN channel_code = 'TGPP' THEN 'Wholesale'
    ELSE 'Other'
  END AS channel_type,
  
  CASE
    WHEN channel_code = 'Online' THEN TRUE ELSE FALSE
  END AS is_online,
  
  -- Audit
  CURRENT_TIMESTAMP AS created_at
  
FROM {{ ref('seed_channel_map') }}


