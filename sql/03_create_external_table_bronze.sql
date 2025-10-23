-- Create External Hive Table pointing to Bronze Raw Parquet files
-- This table allows Trino to query Parquet files without copying data

CREATE TABLE IF NOT EXISTS minio.default.sales_snapshot_raw (
  month VARCHAR,
  week VARCHAR,
  site VARCHAR,
  branch_id VARCHAR,
  channel_id VARCHAR,
  distribution_channel VARCHAR,
  distribution_channel_code VARCHAR,
  sold_quantity VARCHAR,
  cost_price VARCHAR,
  net_price VARCHAR,
  customer_id VARCHAR,
  product_id VARCHAR
)
WITH (
  format = 'PARQUET',
  external_location = 's3a://bronze/raw/sales_snapshot/'
);
