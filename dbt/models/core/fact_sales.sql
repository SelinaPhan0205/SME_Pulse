{{
  config(
    materialized='table',
    schema='core',
    table_format='iceberg',
    partitioned_by=['month_key']
  )
}}

WITH base AS (
  SELECT * FROM {{ ref('stg_sales_snapshot') }}
)
SELECT
    COALESCE(month_raw, 'unknown')       AS month_key,
    COALESCE(site, 'unknown')            AS site,
    COALESCE(product_id, 'unknown')      AS product_id,
    SUM(COALESCE(sold_quantity, 0))      AS qty_sold,
    SUM(COALESCE(total_revenue, 0))      AS revenue,
    SUM(COALESCE(total_cost, 0))         AS cost,
    SUM(COALESCE(gross_profit, 0))       AS gross_profit
FROM base
GROUP BY 1, 2, 3
