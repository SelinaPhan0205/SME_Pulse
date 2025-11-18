-- =====================================================
-- Create Bronze External Tables (Hive Connector)
-- =====================================================
-- Purpose: Tạo external tables trong catalog 'minio' (Hive connector)
--          trỏ vào parquet files đã ingest vào MinIO
-- 
-- Run: docker exec -i sme-trino trino < sql/01_create_bronze_external_tables.sql
-- =====================================================

-- 1. Bank Transactions
DROP TABLE IF EXISTS minio.default.bank_txn_raw;

CREATE TABLE IF NOT EXISTS minio.default.bank_txn_raw (
    csvbase_row_id      BIGINT,
    acct_ccy            VARCHAR,
    acct_id             VARCHAR,
    bal_aftr_bookg      DOUBLE,
    bal_aftr_bookg_nmrc BIGINT,
    bookg_amt           DOUBLE,
    bookg_amt_nmrc      BIGINT,
    bookg_cdt_dbt_ind   VARCHAR,
    bookg_dt_tm_cet     VARCHAR,
    bookg_dt_tm_gmt     TIMESTAMP,
    booking_id          VARCHAR,
    card_poi_id         VARCHAR,
    cdtr_schme_id       VARCHAR,
    ctpty_acct_ccy      VARCHAR,
    ctpty_acct_id_bban  VARCHAR,
    ctpty_acct_id_iban  VARCHAR,
    ctpty_adr_line1     VARCHAR,
    ctpty_adr_line2     DOUBLE,
    ctpty_agt_bic       VARCHAR,
    ctpty_ctry          VARCHAR,
    ctpty_nm            VARCHAR,
    dtld_tx_tp          BIGINT,
    end_to_end_id       VARCHAR,
    ntry_seq_nb         BIGINT,
    rmt_inf_ustrd1      VARCHAR,
    rmt_inf_ustrd2      DOUBLE,
    tx_acct_svcr_ref    VARCHAR,
    tx_tp               DOUBLE,
    year_month          BIGINT,
    ingested_at         TIMESTAMP,
    ingested_year_month VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/bank_txn_raw/'
);

-- 2. Shipments & Payments
DROP TABLE IF EXISTS minio.default.shipments_payments_raw;

CREATE TABLE IF NOT EXISTS minio.default.shipments_payments_raw (
    order_id                VARCHAR,
    customer_id             VARCHAR,
    customer_name           VARCHAR,
    order_date              TIMESTAMP,
    order_status            VARCHAR,
    order_amount            DOUBLE,
    payment_method          VARCHAR,
    payment_status          VARCHAR,
    payment_date            TIMESTAMP,
    shipping_address        VARCHAR,
    shipping_city           VARCHAR,
    shipping_country        VARCHAR,
    shipping_date           TIMESTAMP,
    delivery_date           TIMESTAMP,
    carrier                 VARCHAR,
    tracking_number         VARCHAR,
    ingested_at             TIMESTAMP,
    ingested_year_month     VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/shipments_payments_raw/'
);

-- 3. Invoices AR
DROP TABLE IF EXISTS minio.default.invoices_ar_raw;

CREATE TABLE IF NOT EXISTS minio.default.invoices_ar_raw (
    business_code           VARCHAR,
    cust_number             VARCHAR,
    name_customer           VARCHAR,
    clear_date              VARCHAR,
    buisness_year           DOUBLE,
    doc_id                  DOUBLE,
    posting_date            VARCHAR,
    document_create_date    BIGINT,
    "document_create_date.1" BIGINT,
    due_in_date             DOUBLE,
    invoice_currency        VARCHAR,
    "document type"         VARCHAR,
    posting_id              DOUBLE,
    area_business           DOUBLE,
    total_open_amount       DOUBLE,
    baseline_create_date    DOUBLE,
    cust_payment_terms      VARCHAR,
    invoice_id              DOUBLE,
    isOpen                  BIGINT
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/invoices_AR/'
);

-- 4. Sales Snapshot
DROP TABLE IF EXISTS minio.default.sales_snapshot_raw;

CREATE TABLE IF NOT EXISTS minio.default.sales_snapshot_raw (
    month                       BIGINT,
    week                        BIGINT,
    site                        BIGINT,
    branch_id                   BIGINT,
    channel_id                  VARCHAR,
    distribution_channel        VARCHAR,
    distribution_channel_code   VARCHAR,
    sold_quantity               BIGINT,
    cost_price                  BIGINT,
    net_price                   BIGINT,
    customer_id                 VARCHAR,
    product_id                  VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/sales_snapshot/'
);

-- Verify tables created
SHOW TABLES FROM minio.default;

-- 5. Vietnam Provinces
DROP TABLE IF EXISTS minio.default.vietnam_provinces_raw;

CREATE TABLE IF NOT EXISTS minio.default.vietnam_provinces_raw (
    code                BIGINT,
    name                VARCHAR,
    name_en             VARCHAR,
    full_name           VARCHAR,
    full_name_en        VARCHAR,
    code_name           VARCHAR,
    province_code       BIGINT,
    administrative_unit_id BIGINT,
    ingested_at         TIMESTAMP
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/vietnam_provinces/provinces/'
);

-- 6. Vietnam Districts
DROP TABLE IF EXISTS minio.default.vietnam_districts_raw;

CREATE TABLE IF NOT EXISTS minio.default.vietnam_districts_raw (
    code                BIGINT,
    name                VARCHAR,
    name_en             VARCHAR,
    full_name           VARCHAR,
    full_name_en        VARCHAR,
    code_name           VARCHAR,
    province_code       BIGINT,
    administrative_unit_id BIGINT,
    ingested_at         TIMESTAMP
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-lake/bronze/raw/vietnam_provinces/districts/'
);

-- Verify tables created
SHOW TABLES FROM minio.default;

-- Test queries - count rows in each table
SELECT COUNT(*) as bank_txn_count FROM minio.default.bank_txn_raw;
SELECT COUNT(*) as shipments_count FROM minio.default.shipments_payments_raw;
SELECT COUNT(*) as invoices_ar_count FROM minio.default.invoices_ar_raw;
SELECT COUNT(*) as sales_snapshot_count FROM minio.default.sales_snapshot_raw;
SELECT COUNT(*) as provinces_count FROM minio.default.vietnam_provinces_raw;
SELECT COUNT(*) as districts_count FROM minio.default.vietnam_districts_raw;
