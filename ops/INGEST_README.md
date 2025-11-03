# SME Pulse – Data Ingest Scripts

> Hướng dẫn ingest dữ liệu từ `data/raw/*.csv` lên MinIO (Bronze Layer)

---

## 📋 Overview

| Script | Nguồn | Đích | Rows | Size |
|--------|-------|------|------|------|
| `ingest_bank_transactions.py` | `data/raw/Bank-Transactions.csv` | `s3://sme-lake/bronze/raw/bank_txn_raw/` | ~288k | ~41MB |
| `ingest_shipments_payments.py` | `data/raw/shipments_payments.csv` | `s3://sme-lake/bronze/raw/shipments_payments_raw/` | ~100k | ~85MB |

**Orchestrator**: `run_all_ingest.py` - Chạy cả 2 scripts tuần tự

---

## 🚀 Cách chạy

### 1️⃣ Cài dependencies

```bash
pip install -r ops/requirements_ingest.txt
```

### 2️⃣ Chạy ingest (option A: Chạy cả 2)

```bash
cd "d:\SinhVien\UIT_HocChinhKhoa\HK1 2025 - 2026\SME pulse project"
python ops/run_all_ingest.py
```

**Output ví dụ**:
```
[2025-11-02 10:30:45] INFO - ✅ Connected to MinIO: localhost:9000
[2025-11-02 10:30:46] INFO - ✅ Bucket exists: sme-lake
[2025-11-02 10:30:46] INFO - 📖 Reading CSV: .../data/raw/Bank-Transactions.csv
[2025-11-02 10:30:47] INFO -   Chunk 1: 50000 rows
[2025-11-02 10:30:48] INFO -   Normalizing 50000 rows...
[2025-11-02 10:30:49] INFO -   ✅ Uploaded: bronze/raw/bank_txn_raw/year_month=202406/bank_txn_chunk_0001.parquet
...
[2025-11-02 10:35:22] INFO - ✅ INGEST COMPLETED
[2025-11-02 10:35:22] INFO -   Total rows: 288,810
[2025-11-02 10:35:22] INFO -   Chunks uploaded: 6
```

### 3️⃣ Chạy ingest (option B: Chạy riêng lẻ)

```bash
# Bank transactions chỉ
python ops/ingest_bank_transactions.py

# Hoặc shipments/payments chỉ
python ops/ingest_shipments_payments.py

# Skip bank, chạy chỉ shipments
python ops/run_all_ingest.py --skip-bank

# Skip shipments, chạy chỉ bank
python ops/run_all_ingest.py --skip-shipments
```

---

## 📊 Script Chi tiết

### `ingest_bank_transactions.py`

**Mapping cột**:
```
Source Column           → Bronze Column (Chuẩn hoá)
booking_id              → txn_id (transaction ID)
bookg_dt_tm_gmt         → txn_ts (UTC timestamp)
bookg_amt_nmrc          → amount_eur (numeric amount)
acct_ccy                → currency
bookg_cdt_dbt_ind       → direction (CRDT=in, DBIT=out)
ctpty_nm                → counterparty_name
end_to_end_id           → end_to_end_id (reference)
year_month              → partition key
```

**Chuẩn hoá**:
- ✅ Kiểu dữ liệu: date → datetime, amount → numeric
- ✅ Missing values: Fill với UNKNOWN / empty string
- ✅ Metadata: `ingested_at`, `ingested_year_month`

**Partitioning**: 
```
s3://sme-lake/bronze/raw/bank_txn_raw/
  └─ year_month=202406/
     ├─ bank_txn_chunk_0001.parquet
     ├─ bank_txn_chunk_0002.parquet
     └─ ...
```

---

### `ingest_shipments_payments.py`

**Mapping cột**:
```
Source Column           → Bronze Column (Chuẩn hoá)
Transaction_ID          → txn_id
Customer_ID             → customer_id
Email                   → email_norm (lowercase)
Phone                   → phone_norm (chỉ digits)
Date                    → txn_date (datetime)
Amount                  → amount_vnd (numeric)
Shipping_Method         → carrier (map: Same-Day→GHN, Express→GHTK, Standard→VTP)
Payment_Method          → payment_method (map: card/cash/transfer/vietqr/momo/zalopay)
Order_Status            → status (map: pending/processing/shipped/delivered)
Product_Category        → product_category
Product_Brand           → product_brand
Year, Month             → partition keys
```

**Chuẩn hoá**:
- ✅ Email: lowercase + trim
- ✅ Phone: chỉ lấy digits (remove special chars)
- ✅ Danh mục VN:
  - Carrier: GHN, GHTK, VTP (thay vì Same-Day/Express/Standard)
  - Payment: card, cash, transfer, vietqr, momo, zalopay (thay vì Credit Card/PayPal/etc.)
  - Status: pending, processing, shipped, delivered (chuẩn hoá case)
- ✅ Kiểu dữ liệu: date → datetime, amount → numeric
- ✅ Missing values: Fill với mặc định hoặc "OTHER"
- ✅ Metadata: `ingested_at`, `ingested_year_month`

**Partitioning**:
```
s3://sme-lake/bronze/raw/shipments_payments_raw/
  └─ year_month=202406/
     ├─ shipments_payments_chunk_0001.parquet
     ├─ shipments_payments_chunk_0002.parquet
     └─ ...
```

---

## 🔧 Environment Variables (tuỳ chọn)

```bash
# MinIO connection (mặc định từ docker-compose)
export MINIO_HOST="localhost:9000"              # hoặc "minio:9000" (trong Docker)
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin123"
```

Nếu chạy **trong Docker** (Airflow container):
```bash
export MINIO_HOST="minio:9000"     # Internal network
```

Nếu chạy **local** (development):
```bash
export MINIO_HOST="localhost:9000"  # Localhost
```

---

## 📝 Logs & Troubleshooting

### ✅ Success Log
```
[2025-11-02 10:30:45] INFO - ✅ Connected to MinIO: localhost:9000
[2025-11-02 10:30:46] INFO - ✅ Bucket exists: sme-lake
[2025-11-02 10:30:47] INFO - 📖 Reading CSV: .../data/raw/Bank-Transactions.csv
...
[2025-11-02 10:35:22] INFO - ✅ INGEST COMPLETED
```

### ❌ MinIO Connection Error
```
❌ Failed to connect MinIO: Connection refused
```

**Fix**:
- Kiểm tra MinIO đang chạy: `docker ps | grep minio`
- Kiểm tra host/port: `docker-compose ps`
- Kiểm tra env var: `echo $MINIO_HOST`

### ❌ File Not Found
```
❌ CSV file not found: .../data/raw/Bank-Transactions.csv
```

**Fix**:
- Kiểm tra file tồn tại: `ls -la data/raw/`
- Kiểm tra path: Phải chạy từ **project root** (`SME pulse project/`)

### ❌ Memory Error (Parquet Convert)
```
MemoryError: Unable to allocate X GiB for an array
```

**Fix**:
- Script đã xử lý bằng **chunks** (50k rows/chunk)
- Nếu vẫn lỗi, giảm chunksize: Sửa `chunksize=25000` trong `read_csv_in_chunks()`

---

## ✅ Definition of Done (DoD)

- [ ] 2 scripts tạo OK
- [ ] Dependencies cài OK: `pip install -r ops/requirements_ingest.txt`
- [ ] MinIO chạy OK: `docker-compose ps | grep minio`
- [ ] Bank transactions ingest OK: `python ops/ingest_bank_transactions.py`
- [ ] Shipments/payments ingest OK: `python ops/ingest_shipments_payments.py`
- [ ] Verify files trong MinIO:
  ```bash
  # Bằng MinIO CLI
  mc ls minio/sme-lake/bronze/raw/
  ```
- [ ] Verify dữ liệu trong Trino:
  ```sql
  SELECT COUNT(*) FROM bronze.bank_txn_raw;
  SELECT COUNT(*) FROM bronze.shipments_payments_raw;
  ```
- [ ] Documentation README OK

---

## 📚 Next Steps

1. **dbt Bronze Models** (read parquet từ MinIO)
   ```bash
   dbt run --select bronze.*
   ```

2. **dbt Silver Models** (transform → staging)
   ```bash
   dbt run --select silver.*
   ```

3. **dbt Tests** (data quality)
   ```bash
   dbt test
   ```

4. **Airflow DAG** (orchestrate ingest + dbt)
   - Tạo `airflow/dags/ingest_bronze_daily.py`
   - Schedule: `@daily` hoặc `@weekly`

---

**Status**: ✅ Ready to use  
**Last Updated**: 2025-11-02  
**Maintainer**: SME Pulse Data Team
