-- =====================================================================
-- 📂 GOLD LAYER - DIMENSIONS & FACTS
-- Schema: gold (iceberg.gold.*)
-- Purpose: Star schema cho BI/ML - conformed dimensions + grain facts
-- =====================================================================

-- =====================================================================
-- 🗓️ DIM_DATE: Calendar dimension (SCD Type 0)
-- =====================================================================
-- File: models/gold/dims/dim_date.sql
{{
  config(
    materialized='table',
    schema='gold',
    tags=['dimension', 'scd0']
  )
}}

WITH date_spine AS (
  -- Generate date range: 2022-01-01 to 2026-12-31
  SELECT 
    SEQUENCE(DATE '2022-01-01', DATE '2026-12-31', INTERVAL '1' DAY) AS date_array
),

dates AS (
  SELECT date_val
  FROM date_spine
  CROSS JOIN UNNEST(date_array) AS t(date_val)
),

date_attributes AS (
  SELECT
    -- Surrogate Key
    CAST(date_format(date_val, '%Y%m%d') AS BIGINT) AS date_key,
    
    -- Natural Key
    date_val AS date_actual,
    
    -- Date components
    YEAR(date_val) AS year,
    QUARTER(date_val) AS quarter,
    MONTH(date_val) AS month,
    DAY(date_val) AS day,
    DAY_OF_WEEK(date_val) AS day_of_week_num,
    DAY_OF_YEAR(date_val) AS day_of_year,
    WEEK(date_val) AS week_of_year,
    
    -- Named components (Vietnamese)
    CASE DAY_OF_WEEK(date_val)
      WHEN 1 THEN 'Thứ Hai'
      WHEN 2 THEN 'Thứ Ba'
      WHEN 3 THEN 'Thứ Tư'
      WHEN 4 THEN 'Thứ Năm'
      WHEN 5 THEN 'Thứ Sáu'
      WHEN 6 THEN 'Thứ Bảy'
      WHEN 7 THEN 'Chủ Nhật'
    END AS day_of_week_name_vi,
    
    CASE MONTH(date_val)
      WHEN 1 THEN 'Tháng 1'
      WHEN 2 THEN 'Tháng 2'
      WHEN 3 THEN 'Tháng 3'
      WHEN 4 THEN 'Tháng 4'
      WHEN 5 THEN 'Tháng 5'
      WHEN 6 THEN 'Tháng 6'
      WHEN 7 THEN 'Tháng 7'
      WHEN 8 THEN 'Tháng 8'
      WHEN 9 THEN 'Tháng 9'
      WHEN 10 THEN 'Tháng 10'
      WHEN 11 THEN 'Tháng 11'
      WHEN 12 THEN 'Tháng 12'
    END AS month_name_vi,
    
    CONCAT('Q', CAST(QUARTER(date_val) AS VARCHAR)) AS quarter_name,
    
    -- Fiscal attributes (assuming fiscal year = calendar year)
    YEAR(date_val) AS fiscal_year,
    QUARTER(date_val) AS fiscal_quarter,
    
    -- Business day flags
    CASE 
      WHEN DAY_OF_WEEK(date_val) IN (6, 7) THEN FALSE  -- Sat, Sun
      ELSE TRUE 
    END AS is_weekday,
    
    CASE 
      WHEN DAY_OF_WEEK(date_val) IN (6, 7) THEN TRUE 
      ELSE FALSE 
    END AS is_weekend,
    
    -- Holiday flag (join with seed later)
    FALSE AS is_holiday_placeholder,  -- Will be updated after joining
    
    -- Period indicators
    CASE WHEN DAY(date_val) <= 10 THEN 'Early'
         WHEN DAY(date_val) <= 20 THEN 'Mid'
         ELSE 'Late'
    END AS month_period,
    
    -- First/last day flags
    CASE WHEN DAY(date_val) = 1 THEN TRUE ELSE FALSE END AS is_first_day_of_month,
    CASE WHEN date_val = LAST_DAY_OF_MONTH(date_val) THEN TRUE ELSE FALSE END AS is_last_day_of_month,
    
    -- Relative date markers (for time intelligence)
    CASE WHEN date_val = CURRENT_DATE THEN TRUE ELSE FALSE END AS is_today,
    CASE WHEN date_val = CURRENT_DATE - INTERVAL '1' DAY THEN TRUE ELSE FALSE END AS is_yesterday,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at
    
  FROM dates
)

SELECT 
  da.*,
  -- Join with VN holidays seed
  CASE WHEN h.date IS NOT NULL THEN TRUE ELSE FALSE END AS is_holiday,
  h.holiday_name AS holiday_name_vi
FROM date_attributes da
LEFT JOIN {{ ref('seed_vn_holidays') }} h
  ON da.date_actual = h.date;


-- =====================================================================
-- 🌍 DIM_GEO: Geography dimension - Vietnam locations (SCD Type 1)
-- =====================================================================
-- File: models/gold/dims/dim_geo.sql
{{
  config(
    materialized='table',
    schema='gold',
    tags=['dimension', 'scd1']
  )
}}

WITH geo_base AS (
  SELECT DISTINCT
    -- Surrogate Key (composite: province + district)
    {{ dbt_utils.generate_surrogate_key(['province_code', 'district_code']) }} AS geo_key,
    
    -- Natural Keys
    province_code,
    district_code,
    
    -- Attributes
    province_name,
    district_name,
    region,
    
    -- Derived attributes
    CASE 
      WHEN region = 'Miền Bắc' THEN 'NORTH'
      WHEN region = 'Miền Trung' THEN 'CENTRAL'
      WHEN region = 'Miền Nam' THEN 'SOUTH'
      ELSE 'OTHER'
    END AS region_code,
    
    -- Logistics zones (for shipping optimization)
    CASE
      WHEN province_name IN ('Hà Nội', 'Hải Phòng', 'Quảng Ninh') THEN 'ZONE_1_HANOI'
      WHEN province_name IN ('Hồ Chí Minh', 'Đồng Nai', 'Bình Dương') THEN 'ZONE_2_HCMC'
      WHEN province_name = 'Đà Nẵng' THEN 'ZONE_3_DANANG'
      WHEN region = 'Miền Bắc' THEN 'ZONE_4_NORTH_OTHER'
      WHEN region = 'Miền Nam' THEN 'ZONE_5_SOUTH_OTHER'
      WHEN region = 'Miền Trung' THEN 'ZONE_6_CENTRAL'
      ELSE 'ZONE_9_OTHER'
    END AS logistics_zone,
    
    -- Major city flag
    CASE
      WHEN province_name IN ('Hà Nội', 'Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ') 
      THEN TRUE ELSE FALSE
    END AS is_major_city,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
    
  FROM {{ ref('seed_vietnam_locations') }}
)

SELECT * FROM geo_base;


-- =====================================================================
-- 👤 DIM_CUSTOMER: Customer dimension (SCD Type 2)
-- =====================================================================
-- File: models/gold/dims/dim_customer.sql
{{
  config(
    materialized='incremental',
    unique_key='customer_key',
    schema='gold',
    tags=['dimension', 'scd2']
  )
}}

WITH customer_from_orders AS (
  -- Orders có customer_code
  SELECT DISTINCT
    customer_code AS customer_id,
    NULL AS email,
    NULL AS province_name
  FROM {{ ref('stg_orders_vn') }}
  WHERE customer_code IS NOT NULL
),

customer_from_payments AS (
  -- Payments có email + province
  SELECT DISTINCT
    customer_id,
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

{% if is_incremental() %}
WHERE customer_id NOT IN (SELECT customer_id FROM {{ this }} WHERE is_current = TRUE)
{% endif %};


-- =====================================================================
-- 📦 DIM_PRODUCT: Product dimension (SCD Type 1)
-- =====================================================================
-- File: models/gold/dims/dim_product.sql
{{
  config(
    materialized='incremental',
    unique_key='product_key',
    schema='gold',
    tags=['dimension', 'scd1']
  )
}}

WITH product_from_orders AS (
  SELECT DISTINCT
    product_code AS product_id
  FROM {{ ref('stg_orders_vn') }}
  WHERE product_code IS NOT NULL
),

product_from_payments AS (
  -- Payments có product info chi tiết
  SELECT DISTINCT
    products AS product_id,
    product_category,
    product_brand,
    product_type
  FROM {{ ref('stg_payments_vn') }}
  WHERE products IS NOT NULL
),

product_union AS (
  SELECT product_id, NULL AS product_category, NULL AS product_brand, NULL AS product_type
  FROM product_from_orders
  UNION
  SELECT product_id, product_category, product_brand, product_type
  FROM product_from_payments
),

product_consolidated AS (
  SELECT
    product_id,
    MAX(product_category) AS product_category,
    MAX(product_brand) AS product_brand,
    MAX(product_type) AS product_type
  FROM product_union
  GROUP BY product_id
),

product_enriched AS (
  SELECT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(['product_id']) }} AS product_key,
    
    -- Natural Key
    product_id,
    
    -- Attributes
    COALESCE(product_category, 'Unknown') AS product_category,
    COALESCE(product_brand, 'Unknown') AS product_brand,
    COALESCE(product_type, 'Unknown') AS product_type,
    
    -- Derived: Product hierarchy
    CASE
      WHEN LOWER(product_category) LIKE '%electronic%' THEN 'Electronics'
      WHEN LOWER(product_category) LIKE '%clothing%' OR LOWER(product_category) LIKE '%fashion%' THEN 'Fashion'
      WHEN LOWER(product_category) LIKE '%food%' OR LOWER(product_category) LIKE '%grocery%' THEN 'FMCG'
      WHEN LOWER(product_category) LIKE '%home%' OR LOWER(product_category) LIKE '%decor%' THEN 'Home & Living'
      ELSE 'Other'
    END AS product_division,
    
    -- Active flag
    TRUE AS is_active,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
    
  FROM product_consolidated
)

SELECT * FROM product_enriched

{% if is_incremental() %}
WHERE product_id NOT IN (SELECT product_id FROM {{ this }})
{% endif %};


-- =====================================================================
-- 📺 DIM_CHANNEL: Sales channel dimension (SCD Type 0)
-- =====================================================================
-- File: models/gold/dims/dim_channel.sql
{{
  config(
    materialized='table',
    schema='gold',
    tags=['dimension', 'scd0']
  )
}}

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
  
FROM {{ ref('seed_channel_map') }};


-- =====================================================================
-- 💳 DIM_PAYMENT_METHOD: Payment method dimension (SCD Type 0)
-- =====================================================================
-- File: models/gold/dims/dim_payment_method.sql
{{
  config(
    materialized='table',
    schema='gold',
    tags=['dimension', 'scd0']
  )
}}

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
  
FROM {{ ref('seed_payment_method_map') }};


-- =====================================================================
-- 🚚 DIM_CARRIER: Shipping carrier dimension (SCD Type 0)
-- =====================================================================
-- File: models/gold/dims/dim_carrier.sql
{{
  config(
    materialized='table',
    schema='gold',
    tags=['dimension', 'scd0']
  )
}}

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
  
FROM {{ ref('seed_carrier_map') }};


-- =====================================================================
-- =====================================================================
-- 📊 FACTS LAYER
-- =====================================================================
-- =====================================================================


-- =====================================================================
-- 📦 FACT_ORDERS: Order transactions (wholesale/distribution channel)
-- Grain: 1 row = 1 order line item
-- =====================================================================
-- File: models/gold/facts/fact_orders.sql
{{
  config(
    materialized='incremental',
    unique_key='order_id',
    schema='gold',
    partition_by=['order_date'],
    tags=['fact', 'orders']
  )
}}

WITH orders_enriched AS (
  SELECT
    -- Natural Key
    o.order_id_nat AS order_id,
    
    -- Date dimension FK
    CAST(date_format(CAST(o.order_date AS DATE), '%Y%m%d') AS BIGINT) AS date_key,
    o.order_date,
    
    -- Dimension FKs
    {{ dbt_utils.generate_surrogate_key(['o.customer_code']) }} AS customer_key,
    {{ dbt_utils.generate_surrogate_key(['o.product_code']) }} AS product_key,
    COALESCE(o.channel_code, 'OTHER') AS channel_key,
    
    -- Location FK (from branch_id to geo - assuming branch maps to province)
    -- Note: This is a simplification - in real scenario, need branch -> geo mapping
    NULL AS geo_key,  -- Placeholder
    
    -- Degenerate dimensions (low cardinality, store in fact)
    o.site,
    o.branch_id,
    o.month_raw,
    o.week_raw,
    
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

{% if is_incremental() %}
WHERE order_date > (SELECT COALESCE(MAX(order_date), DATE '1970-01-01') FROM {{ this }})
{% endif %};


-- =====================================================================
-- 💰 FACT_PAYMENTS: Payment transactions (retail channel)
-- Grain: 1 row = 1 payment transaction
-- =====================================================================
-- File: models/gold/facts/fact_payments.sql
{{
  config(
    materialized='incremental',
    unique_key='payment_id',
    schema='gold',
    partition_by=['payment_date'],
    tags=['fact', 'payments', 'retail']
  )
}}

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
    {{ dbt_utils.generate_surrogate_key(['p.province_name', 'p.district_name']) }} AS geo_key,
    
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

{% if is_incremental() %}
WHERE payment_date > (SELECT COALESCE(MAX(payment_date), DATE '1970-01-01') FROM {{ this }})
{% endif %};


-- =====================================================================
-- 📦 FACT_SHIPMENTS: Shipping/delivery transactions
-- Grain: 1 row = 1 shipment
-- =====================================================================
-- File: models/gold/facts/fact_shipments.sql
{{
  config(
    materialized='incremental',
    unique_key='shipment_id',
    schema='gold',
    partition_by=['order_date'],
    tags=['fact', 'shipments', 'logistics']
  )
}}

WITH shipments_enriched AS (
  SELECT
    -- Natural Key
    s.shipment_id_nat AS shipment_id,
    s.transaction_id,  -- Link to payment
    
    -- Date dimension FK
    CAST(date_format(s.order_date, '%Y%m%d') AS BIGINT) AS date_key,
    s.order_date,
    s.order_time,
    
    -- Dimension FKs
    {{ dbt_utils.generate_surrogate_key(['s.customer_id']) }} AS customer_key,
    COALESCE(s.carrier_code, 'OTHER') AS carrier_key,
    {{ dbt_utils.generate_surrogate_key(['s.delivery_province', 's.delivery_district']) }} AS geo_key,
    
    -- Degenerate dimensions
    s.email_norm AS customer_email,
    s.shipping_method_src,
    s.delivery_status_std,
    s.order_status_src,
    s.service_level,
    
    -- Measures
    s.order_value_vnd,
    s.estimated_delivery_days,
    
    -- Geography
    s.delivery_province,
    s.delivery_district,
    s.delivery_region,
    s.shipping_zone,
    
    -- Product context
    s.product_category,
    s.product_brand,
    s.product_type,
    s.products,
    
    -- Customer satisfaction
    s.ratings,
    s.feedback,
    s.delivery_satisfaction_level,
    
    -- Flags
    s.is_priority_shipping,
    CASE WHEN s.delivery_status_std = 'DELIVERED' THEN TRUE ELSE FALSE END AS is_delivered,
    CASE WHEN s.delivery_status_std = 'CANCELLED' THEN TRUE ELSE FALSE END AS is_cancelled,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at
    
  FROM {{ ref('stg_shipments_vn') }} s
)

SELECT * FROM shipments_enriched

{% if is_incremental() %}
WHERE order_date > (SELECT COALESCE(MAX(order_date), DATE '1970-01-01') FROM {{ this }})
{% endif %};


-- =====================================================================
-- 🏦 FACT_BANK_TXN: Bank transactions (cash flow monitoring)
-- Grain: 1 row = 1 bank transaction
-- =====================================================================
-- File: models/gold/facts/fact_bank_txn.sql
{{
  config(
    materialized='incremental',
    unique_key='txn_id',
    schema='gold',
    partition_by=['txn_date'],
    tags=['fact', 'bank', 'cashflow']
  )
}}

WITH bank_txn_enriched AS (
  SELECT
    -- Natural Key
    b.txn_id_nat AS txn_id,
    
    -- Date dimension FK
    CAST(date_format(b.txn_date, '%Y%m%d') AS BIGINT) AS date_key,
    b.txn_date,
    b.txn_ts_local AS txn_timestamp,
    
    -- Degenerate dimensions
    b.ccy AS currency_code,
    b.direction_in_out,
    b.counterparty_name,
    b.end_to_end_id,
    
    -- Measures (additive)
    b.amount_src AS amount_original,
    b.amount_vnd,
    
    -- Derived measures
    CASE 
      WHEN b.direction_in_out = 'in' THEN b.amount_vnd ELSE 0 
    END AS cash_inflow_vnd,
    
    CASE 
      WHEN b.direction_in_out = 'out' THEN ABS(b.amount_vnd) ELSE 0 
    END AS cash_outflow_vnd,
    
    -- Flags
    CASE WHEN b.direction_in_out = 'in' THEN TRUE ELSE FALSE END AS is_inflow,
    CASE WHEN ABS(b.amount_vnd) > 100000000 THEN TRUE ELSE FALSE END AS is_large_transaction,  -- >100M VND
    
    -- Transaction classification (for cash flow forecasting)
    CASE
      WHEN b.direction_in_out = 'in' AND b.counterparty_name LIKE '%CUSTOMER%' THEN 'RECEIVABLE'
      WHEN b.direction_in_out = 'in' THEN 'OTHER_INCOME'
      WHEN b.direction_in_out = 'out' AND b.counterparty_name LIKE '%SUPPLIER%' THEN 'PAYABLE'
      WHEN b.direction_in_out = 'out' AND b.counterparty_name LIKE '%SALARY%' THEN 'PAYROLL'
      WHEN b.direction_in_out = 'out' THEN 'OTHER_EXPENSE'
      ELSE 'UNCLASSIFIED'
    END AS transaction_category,
    
    -- Audit
    b.stg_loaded_at AS source_loaded_at,
    CURRENT_TIMESTAMP AS created_at
    
  FROM {{ ref('stg_bank_txn') }} b
)

SELECT * FROM bank_txn_enriched

{% if is_incremental() %}
WHERE txn_date > (SELECT COALESCE(MAX(txn_date), DATE '1970-01-01') FROM {{ this }})
{% endif %};


-- =====================================================================
-- 📋 SUMMARY: Gold Layer Design
-- =====================================================================
-- 
-- DIMENSIONS (7 tables):
-- ✅ dim_date           - 1,826 rows (2022-2026)
-- ✅ dim_geo            - ~691 rows (VN provinces/districts)
-- ✅ dim_customer       - Dynamic (SCD2)
-- ✅ dim_product        - Dynamic (SCD1)
-- ✅ dim_channel        - ~4 rows (Online, CHTT, TGPP, BANLE)
-- ✅ dim_payment_method - ~8 rows (cash, card, vietqr, momo, etc)
-- ✅ dim_carrier        - ~4 rows (GHN, GHTK, VTP, VNP)
--
-- FACTS (4 tables):
-- ✅ fact_orders        - Wholesale/distribution orders
-- ✅ fact_payments      - Retail payment transactions
-- ✅ fact_shipments     - Delivery/logistics data
-- ✅ fact_bank_txn      - Bank account transactions (cash flow)
--
-- KEY FEATURES:
-- - Star schema compliant (dims + facts)
-- - Conformed dimensions (shared across facts)
-- - Surrogate keys for dims, natural keys preserved
-- - Partitioned by date for performance
-- - Incremental materialization for facts
-- - Vietnamese localization (names, holidays, regions)
-- - Ready for BI tools (Power BI, Tableau, Looker)
-- - Supports ML pipelines (Prophet, Isolation Forest, AR scoring)
-- =====================================================================

