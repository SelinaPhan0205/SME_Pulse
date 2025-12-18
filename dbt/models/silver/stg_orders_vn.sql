{{ config(
    materialized = 'incremental',
    schema = 'silver',
    unique_key = 'order_id_nat',
    on_schema_change = 'sync_all_columns',
    tags = ['silver','orders','feature_store']
) }}

-- depends_on: {{ ref('seed_channel_map') }}

with src as (
  select * from {{ source('bronze', 'sales_snapshot_raw') }}
),

clean AS (
  SELECT
    concat(
      substr(cast(month as varchar), 1, 4), '-',                         -- năm
      lpad(ltrim(substr(cast(month as varchar), 5, 3), '0'), 2, '0')     -- tháng (đủ 2 chữ số)
    ) AS order_date,

    month AS month_raw,
    week AS week_raw,
    {{ dbt_utils.generate_surrogate_key(['month','week','site','branch_id','customer_id','product_id']) }} AS order_id_nat,
    site,
    branch_id,
    trim(distribution_channel_code) AS channel_src,
    customer_id AS customer_code,
    product_id AS product_code,
    greatest(try_cast(sold_quantity AS double), 0) AS qty,
    greatest(try_cast(cost_price AS double), 0) AS unit_cost,
    greatest(try_cast(net_price AS double), 0) AS unit_price
  FROM src
),

vn AS (
  SELECT
    order_date,
    order_id_nat,
    site,
    branch_id,
    map.channel_code,
    customer_code,
    product_code,
    qty,
    unit_cost,
    unit_price,
    qty * unit_price AS revenue,
    qty * unit_cost AS cost,
    (qty * unit_price - qty * unit_cost) AS gross_profit
  FROM clean
  LEFT JOIN {{ ref('seed_channel_map') }} map
    ON lower(trim(clean.channel_src)) = lower(trim(map.source_value))
)

SELECT *
FROM vn
{% if is_incremental() %}
WHERE order_date > (SELECT coalesce(cast(max(order_date) as varchar), '1970-01')FROM {{ this }})
{% endif %}
