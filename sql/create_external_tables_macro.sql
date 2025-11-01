-- ===================================================
-- External Tables cho World Bank & Vietnam Provinces
-- ===================================================
-- Purpose: Tạo external tables trỏ đến bronze layer trên MinIO
-- Run: docker compose exec trino trino < sql/create_external_tables_macro.sql
-- ===================================================

-- 1. World Bank indicators (Bronze layer)
-- Note: Files are stored flat (indicator_YYYYMMDD.parquet) not in subfolders
CREATE TABLE IF NOT EXISTS minio.default.world_bank_indicators_raw (
    indicator_code VARCHAR,
    country_code VARCHAR,
    year VARCHAR,
    value DOUBLE,
    ingested_at VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/world_bank/indicators/'
);

-- 2. Vietnam provinces (Bronze layer)
CREATE TABLE IF NOT EXISTS minio.default.vietnam_provinces_raw (
    province_code VARCHAR,
    province_name VARCHAR,
    phone_code VARCHAR,
    division_type VARCHAR,
    codename VARCHAR,
    ingested_at VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/vietnam_provinces/provinces/'
);

-- 3. Vietnam districts (Bronze layer)
CREATE TABLE IF NOT EXISTS minio.default.vietnam_districts_raw (
    district_code VARCHAR,
    district_name VARCHAR,
    province_code VARCHAR,
    division_type VARCHAR,
    codename VARCHAR,
    ingested_at VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/vietnam_provinces/districts/'
);

-- Verify tables created
SELECT table_name, table_type 
FROM minio.information_schema.tables 
WHERE table_schema = 'default' 
  AND table_name LIKE '%raw%'
ORDER BY table_name;
