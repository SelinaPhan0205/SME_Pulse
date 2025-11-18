-- =====================================================
-- Bootstrap Lakehouse Schemas (Iceberg)
-- =====================================================
-- Purpose: Tạo lại schemas bronze/silver/gold trong catalog sme_lake (Iceberg)
--          sau khi reset Docker và mất Hive Metastore metadata
-- 
-- Run: docker exec -it sme-trino trino --execute "$(cat sql/00_bootstrap_schemas.sql)"
-- =====================================================

-- Catalog: sme_lake (Iceberg connector with Hive Metastore)
-- Warehouse location: s3a://sme-lake/

-- 1. Create Bronze schema (raw Iceberg tables)
CREATE SCHEMA IF NOT EXISTS sme_lake.bronze
WITH (
    location = 's3a://sme-lake/bronze/'
);

-- 2. Create Silver schema (cleaned, conformed data)
CREATE SCHEMA IF NOT EXISTS sme_lake.silver
WITH (
    location = 's3a://sme-lake/silver/'
);

-- 3. Create Gold schema (business metrics, aggregates)
CREATE SCHEMA IF NOT EXISTS sme_lake.gold
WITH (
    location = 's3a://sme-lake/gold/'
);

-- Verify schemas created
SHOW SCHEMAS FROM sme_lake;

-- Verify warehouse locations
SELECT 
    catalog_name,
    schema_name,
    location
FROM sme_lake.information_schema.schemata
WHERE schema_name IN ('bronze', 'silver', 'gold')
ORDER BY schema_name;
