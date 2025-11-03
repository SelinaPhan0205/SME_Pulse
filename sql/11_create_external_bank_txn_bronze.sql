-- 1) Kiểm tra catalog/schema hive (ví dụ catalog "minio")
SHOW SCHEMAS FROM minio; -- mong đợi thấy schema "default"

-- 2) Drop existing table if needed
DROP TABLE IF EXISTS minio.default.bank_txn_raw;

-- 3) Tạo external table trỏ vào Parquet ở Bronze (single file)
-- Schema matches actual Parquet file structure
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

-- 4) Kiểm tra count
SELECT COUNT(*) as total_rows FROM minio.default.bank_txn_raw;

-- 5) Kiểm tra nhanh
SELECT * FROM minio.default.bank_txn_raw LIMIT 10;