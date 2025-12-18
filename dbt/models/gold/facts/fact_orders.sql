{{ config(
    materialized = 'table',
    tags = ['gold', 'fact', 'orders']
) }}

-- =====================================================================
-- 📦 FACT_ORDERS: Order transactions (wholesale/distribution channel)
-- Purpose: Sales orders from stg_orders_vn
-- Grain: 1 row = 1 order line item
-- =====================================================================

WITH orders_enriched AS (
  SELECT
    -- Natural Key
    o.order_id_nat AS order_id,
    
    -- Date dimension FK (order_date format: 'YYYY-MM', convert to first day of month)
    CAST(date_format(DATE(o.order_date || '-01'), '%Y%m%d') AS BIGINT) AS date_key,
    DATE(o.order_date || '-01') AS order_date,
    
    -- Dimension FKs
    {{ dbt_utils.generate_surrogate_key(['o.customer_code']) }} AS customer_key,
    {{ dbt_utils.generate_surrogate_key(['o.product_code']) }} AS product_key,
    COALESCE(o.channel_code, 'OTHER') AS channel_key,
    
    -- Degenerate dimensions (low cardinality, store in fact)
    o.site,
    o.branch_id,
    
    -- Measures (additive)
    o.qty AS quantity,
    o.unit_cost,
    o.unit_price,
    o.revenue,
    o.cost,
    o.gross_profit,
    
    -- Derived measures
    CASE WHEN o.qty > 0 THEN o.revenue / o.qty ELSE 0 END AS avg_unit_price,
    CASE WHEN o.revenue > 0 THEN o.gross_profit / o.revenue ELSE 0 END AS profit_margin,
    
    -- Flags
    CASE WHEN o.gross_profit < 0 THEN TRUE ELSE FALSE END AS is_loss_making,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at
    
  FROM {{ ref('stg_orders_vn') }} o
)

SELECT * FROM orders_enriched