-- =====================================================
-- Data Quality Tests for stg_sales_snapshot
-- =====================================================
-- Mục đích: Validate data quality trước khi vào BI
-- Run: Chạy các SELECT queries này trong Trino
-- =====================================================

-- Test 1: Check NOT NULL for critical columns
SELECT 'Test: NOT NULL checks' AS test_name;
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN month_raw IS NULL THEN 1 ELSE 0 END) as null_month_raw,
    SUM(CASE WHEN site IS NULL THEN 1 ELSE 0 END) as null_site,
    SUM(CASE WHEN product_id IS NULL THEN 1 ELSE 0 END) as null_product_id,
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) as null_customer_id,
    SUM(CASE WHEN sold_quantity IS NULL THEN 1 ELSE 0 END) as null_sold_quantity,
    SUM(CASE WHEN cost_price IS NULL THEN 1 ELSE 0 END) as null_cost_price,
    SUM(CASE WHEN net_price IS NULL THEN 1 ELSE 0 END) as null_net_price
FROM silver.core.stg_sales_snapshot;

-- Test 2: Check positive values for quantity and prices
SELECT 'Test: Positive values (sold_quantity >= 0)' AS test_name;
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN sold_quantity < 0 THEN 1 ELSE 0 END) as negative_qty,
    MIN(sold_quantity) as min_qty,
    MAX(sold_quantity) as max_qty
FROM silver.core.stg_sales_snapshot;

-- Test 3: Check positive prices
SELECT 'Test: Positive values (cost_price >= 0)' AS test_name;
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN cost_price < 0 THEN 1 ELSE 0 END) as negative_cost,
    MIN(cost_price) as min_cost,
    MAX(cost_price) as max_cost
FROM silver.core.stg_sales_snapshot;

-- Test 4: Check positive net prices
SELECT 'Test: Positive values (net_price >= 0)' AS test_name;
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN net_price < 0 THEN 1 ELSE 0 END) as negative_net_price,
    MIN(net_price) as min_net_price,
    MAX(net_price) as max_net_price
FROM silver.core.stg_sales_snapshot;

-- Test 5: Check calculated columns
SELECT 'Test: Calculated columns validation' AS test_name;
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN total_cost IS NULL THEN 1 ELSE 0 END) as null_total_cost,
    SUM(CASE WHEN total_revenue IS NULL THEN 1 ELSE 0 END) as null_total_revenue,
    SUM(CASE WHEN gross_profit IS NULL THEN 1 ELSE 0 END) as null_gross_profit
FROM silver.core.stg_sales_snapshot;

-- Test 6: Data quality summary for fact_sales
SELECT 'Test: Fact Sales aggregation' AS test_name;
SELECT 
    COUNT(*) as fact_rows,
    COUNT(DISTINCT month_key) as unique_months,
    COUNT(DISTINCT site) as unique_sites,
    COUNT(DISTINCT product_id) as unique_products,
    SUM(qty_sold) as total_qty,
    SUM(revenue) as total_revenue,
    SUM(cost) as total_cost,
    SUM(gross_profit) as total_profit
FROM silver.core.fact_sales;