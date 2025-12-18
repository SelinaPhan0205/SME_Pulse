-- 1) Kiểm tra catalog/schema hive (ví dụ catalog "minio")
SHOW SCHEMAS FROM minio; -- mong đợi thấy schema "default"

-- 2) Tạo external table trỏ vào Parquet ở Bronze
CREATE TABLE IF NOT EXISTS minio.default.bank_txn (
    csvbase_row_id          INTEGER,
    acct_ccy                VARCHAR,
    acct_id                 VARCHAR,
    bal_aftr_bookg          DOUBLE,
    bal_aftr_bookg_nmrc     BIGINT,
    bookg_amt               DOUBLE,
    bookg_amt_nmrc          BIGINT,
    bookg_cdt_dbt_ind       VARCHAR,
    bookg_dt_tm_cet         VARCHAR,
    bookg_dt_tm_gmt         VARCHAR,
    booking_id              VARCHAR,
    card_poi_id             VARCHAR,
    cdtr_schme_id           VARCHAR,
    ctpty_acct_ccy          VARCHAR,
    ctpty_acct_id_bban      VARCHAR,
    ctpty_acct_id_iban      VARCHAR,
    ctpty_adr_line1         VARCHAR,
    ctpty_adr_line2         VARCHAR,
    ctpty_agt_bic           VARCHAR,
    ctpty_ctry              VARCHAR,
    ctpty_nm                VARCHAR,
    dtld_tx_tp              INTEGER,
    end_to_end_id           VARCHAR,
    ntry_seq_nb             INTEGER,
    rmt_inf_ustrd1          VARCHAR,
    rmt_inf_ustrd2          VARCHAR,
    tx_acct_svcr_ref        VARCHAR,
    tx_tp                   VARCHAR,
    year_month              INTEGER
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://sme-pulse/bronze/raw/bank_txn/'
);

-- 3) Kiểm tra nhanh
SELECT * FROM minio.default.bank_txn LIMIT  10;