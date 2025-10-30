{{
  config(
    materialized='table',
    schema='gold',
    partitioned_by=['month_key'],
    location='s3a://lakehouse/gold/warehouse/marts/fact_sales'
  )
}}

-- =====================================================
-- Gold Layer: Fact Sales (Aggregated for BI)
-- =====================================================
-- Purpose: Aggregated fact table for business intelligence
-- Source: silver.core.stg_transactions (cleaned staging)
-- Target: gold.mart.fact_sales (Iceberg table)
-- Granularity: month × site × product
-- Location: s3a://gold/warehouse/mart/

WITH base AS (
  SELECT * FROM {{ ref('stg_transactions') }}
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
