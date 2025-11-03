{{ config(
    materialized = 'table',
    tags = ['gold', 'fact', 'payments', 'retail']
) }}

-- =====================================================================
-- 💰 FACT_PAYMENTS: Payment transactions (retail channel)
-- Purpose: Retail payment transactions from stg_payments_vn
-- Grain: 1 row = 1 payment transaction
-- =====================================================================

WITH payments_enriched AS (
  SELECT
    -- Natural Key
    p.payment_id_nat AS payment_id,
    
    -- Date dimension FK
    CAST(date_format(p.payment_date, '%Y%m%d') AS BIGINT) AS date_key,
    p.payment_date,
    p.transaction_time,
    
    -- Dimension FKs
    {{ dbt_utils.generate_surrogate_key(['p.customer_id']) }} AS customer_key,
    {{ dbt_utils.generate_surrogate_key(['p.products']) }} AS product_key,
    COALESCE(p.payment_method_code, 'OTHER') AS payment_method_key,
    -- Location key: stg_payments_vn chỉ có province_name + district_name (không có code)
    -- Để NULL, join sau qua province_name + district_name
    CAST(NULL AS VARCHAR) AS location_key,
    
    -- Degenerate dimensions
    p.email_norm AS customer_email,
    p.payment_method_src,
    p.payment_status_std,
    p.order_status_src,
    
    -- Measures (additive)
    p.amount_foreign,
    p.total_amount_foreign,
    p.amount_vnd,
    p.total_amount_vnd,
    
    -- Currency conversion info (semi-additive)
    p.currency_code,
    p.fx_rate_to_vnd,
    
    -- Product context (for cross-sell analysis)
    p.product_category,
    p.product_brand,
    p.product_type,
    
    -- Shipping context
    p.shipping_method_src,
    
    -- Customer satisfaction
    p.ratings,
    p.feedback,
    
    -- Derived measures
    CASE 
      WHEN p.ratings >= 4.5 THEN 'EXCELLENT'
      WHEN p.ratings >= 3.5 THEN 'GOOD'
      WHEN p.ratings >= 2.5 THEN 'AVERAGE'
      ELSE 'POOR'
    END AS satisfaction_level,
    
    -- Flags
    p.is_digital_payment,
    CASE WHEN p.payment_status_std = 'PAID' THEN TRUE ELSE FALSE END AS is_successful_payment,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at
    
  FROM {{ ref('stg_payments_vn') }} p
)

SELECT * FROM payments_enriched
