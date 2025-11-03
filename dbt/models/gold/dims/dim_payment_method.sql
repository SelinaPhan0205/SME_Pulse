{{ config(
    materialized = 'table',
    tags = ['gold', 'dimension', 'scd0']
) }}

-- =====================================================================
-- 💳 DIM_PAYMENT_METHOD: Payment method dimension (SCD Type 0)
-- Purpose: Payment method mapping from seed data
-- Grain: 1 row = 1 payment method
-- =====================================================================

SELECT DISTINCT
  -- Surrogate Key = Natural Key
  method_code AS payment_method_key,
  
  -- Attributes
  method_name_vn,
  is_digital,
  
  -- Derived
  CASE
    WHEN method_code IN ('vietqr', 'momo', 'zalopay', 'transfer') THEN 'E-Wallet/Transfer'
    WHEN method_code = 'card' THEN 'Card'
    WHEN method_code = 'cash' THEN 'Cash'
    ELSE 'Other'
  END AS payment_category,
  
  -- Risk level (for fraud detection)
  CASE
    WHEN method_code = 'cash' THEN 'LOW'
    WHEN method_code IN ('vietqr', 'momo', 'zalopay') THEN 'LOW'
    WHEN method_code = 'card' THEN 'MEDIUM'
    WHEN method_code = 'transfer' THEN 'MEDIUM'
    ELSE 'HIGH'
  END AS risk_level,
  
  -- Audit
  CURRENT_TIMESTAMP AS created_at
  
FROM {{ ref('seed_payment_method_map') }}
