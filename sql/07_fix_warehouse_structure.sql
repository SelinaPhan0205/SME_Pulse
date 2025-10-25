-- =====================================================
-- Fix Iceberg Warehouse Structure
-- =====================================================
-- Vấn đề: silver.core và gold.mart data đang lưu trong bronze/warehouse
-- Giải pháp: Recreate schemas với location explicit
-- =====================================================

-- Step 1: Drop existing schemas (cascade xóa tất cả tables)
DROP SCHEMA IF EXISTS silver.core CASCADE;
DROP SCHEMA IF EXISTS gold.mart CASCADE;

-- Step 2: Create silver.core schema với location tại silver/warehouse
CREATE SCHEMA silver.core 
WITH (location = 's3a://silver/warehouse/core');

-- Step 3: Create gold.mart schema với location tại gold/warehouse
CREATE SCHEMA gold.mart 
WITH (location = 's3a://gold/warehouse/mart');

-- Step 4: Verify schemas
SHOW SCHEMAS IN silver;
SHOW SCHEMAS IN gold;
