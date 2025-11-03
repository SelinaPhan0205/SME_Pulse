{{ config(
    materialized = 'table',
    tags = ['silver', 'bank_txn', 'feature_store']
) }}

-- ========================================================
-- 🌐 Bước 1: Đọc dữ liệu thô từ MinIO (Bronze)
-- ========================================================
WITH src AS (
  SELECT *
  FROM {{ source('bronze', 'bank_txn_raw') }}
),

-- ========================================================
-- 🧹 Bước 2: Chuẩn hóa dữ liệu gốc
-- ========================================================
norm AS (
  SELECT
    CAST(booking_id AS VARCHAR) AS txn_id_nat, -- ID giao dịch tự nhiên
    CAST(bookg_dt_tm_gmt AS TIMESTAMP) AS txn_ts_local, -- giờ VN (tạm thời bỏ timezone)
    CASE 
        WHEN UPPER(bookg_cdt_dbt_ind) = 'CRDT' THEN CAST(bookg_amt_nmrc AS DOUBLE) 
        ELSE -CAST(bookg_amt_nmrc AS DOUBLE)
    END AS amount_src, -- đổi dấu: CRDT = +, DBIT = -
    UPPER(TRIM(acct_ccy)) AS ccy, -- loại tiền tệ
    NULLIF(TRIM(ctpty_nm), '') AS counterparty_name, -- tên đối tác nếu có
    NULLIF(TRIM(end_to_end_id), '') AS end_to_end_id
  FROM src
  WHERE booking_id IS NOT NULL
),

-- ========================================================
-- 💱 Bước 3: Quy đổi VND + xác định hướng dòng tiền
-- ========================================================
vn AS (
  SELECT
    n.txn_id_nat,
    DATE(n.txn_ts_local) AS txn_date,
    n.txn_ts_local,
    n.amount_src,
    n.ccy,
    -- Join với seed tỷ giá để quy đổi về VND
    n.amount_src * COALESCE(f.rate_to_vnd, 1) AS amount_vnd,
    CASE WHEN n.amount_src >= 0 THEN 'in' ELSE 'out' END AS direction_in_out,
    n.counterparty_name,
    n.end_to_end_id,
    CURRENT_TIMESTAMP AS stg_loaded_at
  FROM norm n
  LEFT JOIN {{ ref('seed_fx_rates') }} f
    ON n.ccy = f.currency_code
   AND DATE(n.txn_ts_local) >= CAST(f.effective_date AS DATE)
)

-- ========================================================
-- 📊 Bước 4: Ghi kết quả ra bảng Silver
-- ========================================================
SELECT *
FROM vn
