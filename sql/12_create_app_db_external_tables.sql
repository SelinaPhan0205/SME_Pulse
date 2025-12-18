-- =====================================================
-- CREATE EXTERNAL TABLES FOR APP DB IN TRINO
-- =====================================================
-- Purpose: Create external table definitions in Trino
-- that reference Parquet files in MinIO Bronze layer
-- extracted from PostgreSQL App DB
-- 
-- Tables:
-- - ar_invoices_app_db_raw
-- - payments_app_db_raw
-- - payment_allocations_app_db_raw
-- =====================================================

-- 1) Create external table for AR Invoices
CREATE TABLE IF NOT EXISTS minio.default.ar_invoices_app_db_raw (
    id INTEGER,
    org_id INTEGER,
    invoice_no VARCHAR,
    customer_id INTEGER,
    issue_date DATE,
    due_date DATE,
    total_amount DOUBLE,
    paid_amount DOUBLE,
    status VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-pulse/bronze/raw/app_db/ar_invoices/'
);

-- 2) Create external table for Payments
CREATE TABLE IF NOT EXISTS minio.default.payments_app_db_raw (
    id INTEGER,
    org_id INTEGER,
    transaction_date DATE,
    payment_method VARCHAR,
    amount DOUBLE,
    reference_code VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-pulse/bronze/raw/app_db/payments/'
);

-- 3) Create external table for Payment Allocations
CREATE TABLE IF NOT EXISTS minio.default.payment_allocations_app_db_raw (
    id INTEGER,
    org_id INTEGER,
    payment_id INTEGER,
    ar_invoice_id INTEGER,
    allocated_amount DOUBLE,
    notes VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-pulse/bronze/raw/app_db/payment_allocations/'
);

-- 4) Quick test - check if data is loaded
SELECT COUNT(*) as invoice_count FROM minio.default.ar_invoices_app_db_raw;
SELECT COUNT(*) as payment_count FROM minio.default.payments_app_db_raw;
SELECT COUNT(*) as allocation_count FROM minio.default.payment_allocations_app_db_raw;
