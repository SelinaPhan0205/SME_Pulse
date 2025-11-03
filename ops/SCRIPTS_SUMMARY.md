# 📊 Scripts Vừa Tạo – Data Ingest (Bronze Layer)

## ✅ Status
- [x] Verification script
- [x] Bank transactions ingest script
- [x] Shipments & payments ingest script
- [x] Master orchestrator
- [x] Requirements file
- [x] README & Documentation

---

## 📁 File Structure

```
ops/
├─ ingest_bank_transactions.py      # ▶️ Ingest Bank-Transactions.csv
├─ ingest_shipments_payments.py     # ▶️ Ingest shipments_payments.csv
├─ run_all_ingest.py                # ▶️ Master orchestrator (chạy cả 2)
├─ setup_verify.py                  # ✅ Verification script
├─ requirements_ingest.txt          # 📦 Dependencies
└─ INGEST_README.md                 # 📚 Full documentation
```

---

## 🚀 Quick Start

### 1. Cài dependencies
```bash
pip install -r ops/requirements_ingest.txt
```

### 2. Verify environment
```bash
python ops/setup_verify.py
```

### 3. Chạy ingest (cả 2 files)
```bash
python ops/run_all_ingest.py
```

---

## 📋 Script Details

### `ingest_bank_transactions.py`
- **Input**: `data/raw/Bank-Transactions.csv` (39.5 MB, ~289k rows)
- **Output**: `s3://sme-lake/bronze/raw/bank_txn_raw/year_month=YYYYMM/*.parquet`
- **Process**:
  - ✅ Read CSV in 50k row chunks (memory efficient)
  - ✅ Normalize dates (UTC → datetime)
  - ✅ Convert amounts to numeric
  - ✅ Fill missing values (UNKNOWN, "")
  - ✅ Add metadata (ingested_at, ingested_year_month)
  - ✅ Convert to Parquet
  - ✅ Upload to MinIO (partitioned by year_month)

### `ingest_shipments_payments.py`
- **Input**: `data/raw/shipments_payments.csv` (81 MB, ~100k rows)
- **Output**: `s3://sme-lake/bronze/raw/shipments_payments_raw/year_month=YYYYMM/*.parquet`
- **Process**:
  - ✅ Read CSV in 50k row chunks
  - ✅ Normalize dates (MM/DD/YYYY → datetime)
  - ✅ Normalize email (lowercase, trim)
  - ✅ Normalize phone (digits only)
  - ✅ **Map danh mục Việt**:
    - Shipping: Same-Day→GHN, Express→GHTK, Standard→VTP
    - Payment: card, cash, transfer, vietqr, momo, zalopay
    - Status: pending, processing, shipped, delivered
  - ✅ Convert amounts to numeric
  - ✅ Fill missing values
  - ✅ Add metadata
  - ✅ Convert to Parquet
  - ✅ Upload to MinIO (partitioned)

### `run_all_ingest.py`
- **Purpose**: Master orchestrator - chạy cả 2 scripts tuần tự
- **Options**:
  ```bash
  python ops/run_all_ingest.py                    # Chạy cả 2
  python ops/run_all_ingest.py --skip-bank        # Bỏ bank, chạy shipments
  python ops/run_all_ingest.py --skip-shipments   # Bỏ shipments, chạy bank
  ```
- **Features**:
  - ✅ Formatted logging (timestamps, emojis)
  - ✅ Summary report
  - ✅ Exit code (0=success, 1=failure)

### `setup_verify.py`
- **Purpose**: Verify environment trước khi ingest
- **Checks**:
  - ✅ Python version (>= 3.8)
  - ✅ Project structure
  - ✅ Source CSV files
  - ✅ Python packages (pandas, pyarrow, minio)
  - ✅ MinIO connection
  - ✅ Bucket 'sme-lake' exists
  - ✅ Disk space (> 5 GB)

---

## 🔄 Data Flow

```
data/raw/Bank-Transactions.csv (39.5 MB)
  ↓
ingest_bank_transactions.py (chunk → normalize → parquet)
  ↓
MinIO: s3://sme-lake/bronze/raw/bank_txn_raw/year_month=202406/*.parquet
  ↓
dbt: models/bronze/sources.yml (source declaration)
  ↓
Trino: SELECT * FROM bronze.bank_txn_raw


data/raw/shipments_payments.csv (81 MB)
  ↓
ingest_shipments_payments.py (chunk → normalize → parquet)
  ↓
MinIO: s3://sme-lake/bronze/raw/shipments_payments_raw/year_month=202406/*.parquet
  ↓
dbt: models/bronze/sources.yml
  ↓
Trino: SELECT * FROM bronze.shipments_payments_raw
```

---

## 📝 Environment Variables (tuỳ chọn)

```bash
# MinIO connection
export MINIO_HOST="localhost:9000"              # Local
export MINIO_HOST="minio:9000"                  # Docker
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin123"
```

---

## ✅ Verification Checklist

- [x] Scripts tạo OK
- [x] Python packages available
- [x] MinIO bucket exists
- [x] Source CSV files available
- [x] setup_verify.py passes
- [ ] Run ingest: `python ops/run_all_ingest.py`
- [ ] Verify MinIO: `mc ls minio/sme-lake/bronze/raw/`
- [ ] Verify Trino: `SELECT COUNT(*) FROM bronze.bank_txn_raw;`

---

## 🎯 Next Steps (sau khi ingest xong)

1. **Create dbt Bronze Models** (read from MinIO)
   ```bash
   # models/bronze.yml
   - name: bank_txn_raw
   - name: shipments_payments_raw
   ```

2. **Create dbt Silver Staging Models** (transform & normalize)
   ```bash
   dbt run --select silver.*
   ```

3. **Run dbt Tests**
   ```bash
   dbt test
   ```

4. **Create Airflow DAG** (orchestrate daily)
   ```bash
   # airflow/dags/ingest_bronze_daily.py
   ```

---

## 📞 Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: pandas` | `pip install -r ops/requirements_ingest.txt` |
| `Failed to connect MinIO` | Check MinIO running: `docker-compose ps \| grep minio` |
| `CSV file not found` | Run from project root: `cd "SME pulse project"` |
| `MemoryError` | Reduce chunksize (25000 instead of 50000) |
| `Parquet upload fails` | Check bucket permissions: `mc ls minio/sme-lake` |

---

## 📊 Expected Output

**Bank Transactions**:
```
✅ INGEST COMPLETED
  Total rows: 288,810
  Chunks uploaded: 6
  Files: bronze/raw/bank_txn_raw/year_month=202406/*.parquet
```

**Shipments & Payments**:
```
✅ INGEST COMPLETED
  Total rows: ~100,000
  Chunks uploaded: 2-3
  Files: bronze/raw/shipments_payments_raw/year_month=202406/*.parquet
```

---

## 📚 Documentation

- **Full Guide**: `ops/INGEST_README.md`
- **Script Docstrings**: Read top of each script
- **Logging**: Check console output for detailed logs

---

**Status**: ✅ Ready  
**Created**: 2025-11-02  
**Version**: 1.0
