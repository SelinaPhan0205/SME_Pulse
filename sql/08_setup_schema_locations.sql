-- =====================================================
-- Setup Iceberg Warehouse Locations per Schema
-- =====================================================
-- Mục đích: Set location property cho mỗi schema
-- Trino sẽ respects location khi create Iceberg tables
-- =====================================================

-- Silver schemas
CREATE SCHEMA IF NOT EXISTS silver.core 
WITH (location = 's3a://silver/warehouse/core');

-- Gold schemas  
CREATE SCHEMA IF NOT EXISTS gold.mart 
WITH (location = 's3a://gold/warehouse/mart');

-- Verify
SHOW SCHEMAS IN silver;
SHOW SCHEMAS IN gold;

-- Check schema locations
SELECT schema_name, location 
FROM information_schema.schemata 
WHERE catalog_name IN ('silver', 'gold');
