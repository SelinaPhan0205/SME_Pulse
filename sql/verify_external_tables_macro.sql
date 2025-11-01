-- ===================================================
-- Verify External Tables & Sample Data
-- ===================================================

-- 1. List all external tables
SELECT table_name, table_type 
FROM minio.information_schema.tables 
WHERE table_schema = 'default' 
ORDER BY table_name;

-- 2. Count records in World Bank indicators
SELECT 
    indicator_code,
    COUNT(*) as record_count,
    MIN(year) as earliest_year,
    MAX(year) as latest_year
FROM minio.default.world_bank_indicators_raw
GROUP BY indicator_code
ORDER BY indicator_code;

-- 3. Sample World Bank data
SELECT * 
FROM minio.default.world_bank_indicators_raw 
WHERE indicator_code = 'FP.CPI.TOTL.ZG'
ORDER BY year DESC
LIMIT 5;

-- 4. Count provinces & districts
SELECT 'Provinces' as type, COUNT(*) as count 
FROM minio.default.vietnam_provinces_raw
UNION ALL
SELECT 'Districts' as type, COUNT(*) as count 
FROM minio.default.vietnam_districts_raw;

-- 5. Sample provinces data
SELECT 
    province_code,
    province_name,
    phone_code,
    division_type
FROM minio.default.vietnam_provinces_raw
LIMIT 10;

-- 6. Sample districts data (with province join)
SELECT 
    d.district_code,
    d.district_name,
    p.province_name
FROM minio.default.vietnam_districts_raw d
LEFT JOIN minio.default.vietnam_provinces_raw p
    ON d.province_code = p.province_code
LIMIT 10;
