-- ===================================================================
-- CREATE EXTERNAL TABLE: ar_invoices_raw
-- Bronze layer – Raw AR invoices from CSV → Parquet
-- ===================================================================

CREATE TABLE IF NOT EXISTS minio.default.ar_invoices_raw (
    invoice_id DOUBLE,
    doc_id DOUBLE,
    business_code VARCHAR,
    cust_number VARCHAR,
    name_customer VARCHAR,
    invoice_currency VARCHAR,
    cust_payment_terms VARCHAR,
    total_open_amount DOUBLE,
    isOpen BIGINT,
    posting_id DOUBLE,
    posting_date VARCHAR,
    baseline_create_date DOUBLE,
    due_in_date DOUBLE,
    clear_date VARCHAR,
    document_create_date BIGINT,
    "document_create_date.1" BIGINT,
    "document type" VARCHAR,
    area_business DOUBLE,
    buisness_year DOUBLE
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-pulse/bronze/raw/ar_invoices/'
);


-- Verify the table is registered
SELECT * FROM minio.default.ar_invoices_raw LIMIT 10;
