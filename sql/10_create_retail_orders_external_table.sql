-- ===================================================================
-- CREATE EXTERNAL TABLE: retail_orders_raw
-- Bronze layer - Raw retail orders data from Parquet
-- ===================================================================

CREATE TABLE IF NOT EXISTS minio.default.retail_data_raw (
    transaction_id DOUBLE,
    customer_id DOUBLE,
    name VARCHAR,
    email VARCHAR,
    phone DOUBLE,
    address VARCHAR,
    city VARCHAR,
    state VARCHAR,
    zipcode DOUBLE,
    country VARCHAR,
    age DOUBLE,
    gender VARCHAR,
    income VARCHAR,
    customer_segment VARCHAR,
    date VARCHAR,
    year DOUBLE,
    month VARCHAR,
    time VARCHAR,
    total_purchases DOUBLE,
    amount DOUBLE,
    total_amount DOUBLE,
    product_category VARCHAR,
    product_brand VARCHAR,
    product_type VARCHAR,
    feedback VARCHAR,
    shipping_method VARCHAR,
    payment_method VARCHAR,
    order_status VARCHAR,
    ratings DOUBLE,
    products VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-pulse/bronze/raw/retail_data/'
);

-- Verify table creation
SELECT * FROM minio.default.retail_data_raw LIMIT  10;
