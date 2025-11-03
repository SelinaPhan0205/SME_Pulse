-- ===================================================================
-- CREATE EXTERNAL TABLE: shipments_payments_raw
-- Bronze layer - Raw shipments & payments data from Parquet
-- ===================================================================

-- Drop existing table
DROP TABLE IF EXISTS minio.default.shipments_payments_raw;

-- Create external table (single file)
-- Schema matches actual Parquet file structure
CREATE TABLE IF NOT EXISTS minio.default.shipments_payments_raw (
    Transaction_ID      DOUBLE,
    Customer_ID         DOUBLE,
    Name                VARCHAR,
    Email               VARCHAR,
    Phone               VARCHAR,
    Address             VARCHAR,
    City                VARCHAR,
    State               VARCHAR,
    Zipcode             DOUBLE,
    Country             VARCHAR,
    Age                 DOUBLE,
    Gender              VARCHAR,
    Income              DOUBLE,
    Customer_Segment    VARCHAR,
    Date                TIMESTAMP,
    Year                DOUBLE,
    Month               VARCHAR,
    Time                VARCHAR,
    Total_Purchases     DOUBLE,
    Amount              DOUBLE,
    Total_Amount        DOUBLE,
    Product_Category    VARCHAR,
    Product_Brand       VARCHAR,
    Product_Type        VARCHAR,
    Feedback            VARCHAR,
    Shipping_Method     VARCHAR,
    Payment_Method      VARCHAR,
    Order_Status        VARCHAR,
    Ratings             DOUBLE,
    products            VARCHAR,
    ingested_at         TIMESTAMP,
    ingested_year_month VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/shipments_payments_raw/'
);

-- Verify table creation
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT Transaction_ID) as unique_transactions,
    COUNT(DISTINCT Customer_ID) as unique_customers,
    MIN(Date) as earliest_date,
    MAX(Date) as latest_date
FROM minio.default.shipments_payments_raw;

SELECT * FROM minio.default.shipments_payments_raw LIMIT 5;