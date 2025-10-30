-- 1) Kiểm tra catalog/schema hive (ví dụ catalog "minio")
SHOW SCHEMAS FROM minio; -- mong đợi thấy schema "default"

-- 2) Tạo external table trỏ vào Parquet ở Bronze
CREATE TABLE IF NOT EXISTS minio.default.sales_snapshot_raw (
    month BIGINT,
    week BIGINT,
    site BIGINT,
    branch_id BIGINT,
    channel_id VARCHAR,
    distribution_channel VARCHAR,
    distribution_channel_code VARCHAR,
    sold_quantity BIGINT,
    cost_price BIGINT,
    net_price BIGINT,
    customer_id VARCHAR,
    product_id VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://bronze/raw/sales_snapshot/'
);

-- 3) Kiểm tra nhanh
SELECT * FROM minio.default.sales_snapshot_raw LIMIT 10;
