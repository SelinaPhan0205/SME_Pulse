-- =====================================================
-- Silver Layer: Fact Sales (Aggregated)
-- =====================================================
-- Mục đích: Tạo fact table aggregated theo (month, site, product_id)
-- Granularity: month × site × product
-- Rows expected: ~500-1000 (much smaller than staging)
-- Used by: Metabase dashboards, BI reports
-- =====================================================

CREATE TABLE IF NOT EXISTS silver.core.fact_sales AS
WITH base AS (
    SELECT * FROM silver.core.stg_sales_snapshot
)
SELECT
    COALESCE(month_raw, 'unknown')       AS month_key,
    COALESCE(site, 'unknown')            AS site,
    COALESCE(product_id, 'unknown')      AS product_id,
    SUM(COALESCE(sold_quantity, 0))      AS qty_sold,
    SUM(COALESCE(total_revenue, 0))      AS revenue,
    SUM(COALESCE(total_cost, 0))         AS cost,
    SUM(COALESCE(gross_profit, 0))       AS gross_profit
FROM base
GROUP BY 1, 2, 3;