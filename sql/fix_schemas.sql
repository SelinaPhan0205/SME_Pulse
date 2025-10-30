-- SME Pulse Lakehouse: Migrate tables to new schema structure
-- 1. Move tables from old schemas to new standardized schemas
ALTER TABLE iceberg.core.stg_transactions SET SCHEMA silver;  -- Move staging table to silver
ALTER TABLE iceberg.marts.fact_sales SET SCHEMA gold;         -- Move fact table to gold

-- 2. Verify tables are in the correct schemas
SHOW TABLES FROM iceberg.silver;  -- Should include stg_transactions
SHOW TABLES FROM iceberg.gold;    -- Should include fact_sales

-- 3. Drop old/empty schemas if no longer needed
DROP SCHEMA IF EXISTS iceberg.core;
DROP SCHEMA IF EXISTS iceberg.marts;
-- End of migration script
