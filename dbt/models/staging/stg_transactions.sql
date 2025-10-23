{{
  config(
    materialized='table',
    schema='core',
    table_format='iceberg'
  )
}}

/*
  Silver Layer - Staging Sales Snapshot
  ====================================
  Purpose: Read raw Parquet from Bronze external table, clean and conform
  Source: minio.default.sales_snapshot_raw (External Hive table)
  Target: silver.core.stg_sales_snapshot (Iceberg table)
  
  Data Quality Handling:
  - Convert negative values to 0 (Option 2: COALESCE approach)
  - This preserves row count while cleaning anomalies
*/

WITH src AS (
  SELECT
      CAST(month AS VARCHAR)                         AS month_raw,
      CAST(week AS VARCHAR)                          AS week_raw,
      CAST(site AS VARCHAR)                          AS site,
      CAST(branch_id AS VARCHAR)                     AS branch_id,
      CAST(channel_id AS VARCHAR)                    AS channel_id,
      CAST(distribution_channel AS VARCHAR)          AS distribution_channel,
      CAST(distribution_channel_code AS VARCHAR)     AS distribution_channel_code,
      TRY_CAST(sold_quantity AS DOUBLE)              AS sold_quantity_raw,
      TRY_CAST(cost_price AS DOUBLE)                 AS cost_price_raw,
      TRY_CAST(net_price AS DOUBLE)                  AS net_price_raw,
      CAST(customer_id AS VARCHAR)                   AS customer_id,
      CAST(product_id AS VARCHAR)                    AS product_id
  FROM {{ source('bronze','sales_snapshot_raw') }}
),
cleaned AS (
  SELECT
      month_raw,
      week_raw,
      site,
      branch_id,
      channel_id,
      distribution_channel,
      distribution_channel_code,
      customer_id,
      product_id,
      
      -- Data Quality: Convert negative/NULL values to 0
      CASE 
        WHEN sold_quantity_raw IS NULL THEN 0
        WHEN sold_quantity_raw < 0 THEN 0
        ELSE sold_quantity_raw 
      END AS sold_quantity,
      
      CASE 
        WHEN cost_price_raw IS NULL THEN 0
        WHEN cost_price_raw < 0 THEN 0
        ELSE cost_price_raw 
      END AS cost_price,
      
      CASE 
        WHEN net_price_raw IS NULL THEN 0
        WHEN net_price_raw < 0 THEN 0
        ELSE net_price_raw 
      END AS net_price
  FROM src
)
SELECT
    -- Time dimensions
    month_raw,
    week_raw,
    
    -- Location dimensions
    site,
    branch_id,
    
    -- Channel dimensions
    channel_id,
    distribution_channel,
    distribution_channel_code,
    
    -- Product & Customer
    customer_id,
    product_id,
    
    -- Metrics (cleaned - all >= 0)
    sold_quantity,
    cost_price,
    net_price,
    
    -- Business calculations (based on cleaned values)
    cost_price * sold_quantity              AS total_cost,
    net_price * sold_quantity               AS total_revenue,
    (net_price - cost_price) * sold_quantity AS gross_profit
FROM cleaned
