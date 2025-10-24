# 🚀 Roadmap hoàn chỉnh (tiếng Việt) — SME Pulse Lakehouse
> Mục tiêu: xây dựng pipeline **chuẩn enterprise** cho dữ liệu Kaggle *Sales Snapshot* theo mô hình **Bronze → Silver → Gold → ML**, dùng **MinIO + Trino (Iceberg/Hive) + dbt**.

---

## 0) Chuẩn bị (Prereqs)
- **Docker Compose** stack đã chạy: `minio`, `hive-metastore`, `trino`.
- Trino catalogs đã có: `bronze`(hive, optional), `minio`(hive, đọc bronze), `silver`(iceberg), `gold`(iceberg).  
  Kiểm tra: 
  ```sql
  SHOW CATALOGS;
  ```
- Python env: `pip install -r scripts/requirements.txt`.
- Dataset Excel nằm ở: `data/raw/Sales_snapshot_data/` (19 file).

> **Lưu ý hệ điều hành:**  
> - **Windows PowerShell** dùng **backtick** `` ` `` để xuống dòng.  
> - **macOS/Linux** dùng ký tự `\` để xuống dòng.

---

## 1) Thiết kế thư mục/bucket (Bronze chuẩn enterprise)
### Ý nghĩa
- **bronze/source/**: Lưu **file gốc** (immutable) để audit, lineage.
- **bronze/raw/**: Lưu **Parquet chuẩn hoá nhẹ** để query nhanh về sau (Trino/dbt).

### Cấu trúc mong muốn
```
bronze/
├── source/
│   └── sales_snapshot/
│        ├── TT T01-2022_split_1.xlsx
│        ├── TT T02-2022_split_1.xlsx
│        └── ...
└── raw/
    └── sales_snapshot/
         └── batch_<HHMMSS>.parquet
```

> Các bucket `silver/` và `gold/` **không** cần `warehouse` trong bronze. `warehouse` chỉ là **root catalog** ở **layer tương ứng** (ví dụ `s3://silver/warehouse/`).

---

## 2) Ingest vào Bronze (không “bóp cột”, dữ nguyên schema)
Script chính: **`scripts/ingest_sales_snapshot_batch.py`**
- Upload **toàn bộ Excel gốc** vào `bronze/source/sales_snapshot/`.
- Sinh **một Parquet tổng hợp** vào `bronze/raw/sales_snapshot/batch_<timestamp>.parquet`.
- **Không drop cột**, không đổi tên, chỉ thêm metadata cột `_source_file`, `_ingested_at` nếu cần.

### Chạy lệnh
**Windows PowerShell:**
```powershell
cd scripts
python .\ingest_sales_snapshot_batch.py `
  --folder ..\data\raw\Sales_snapshot_data `
  --prefix sales_snapshot `
  --upload-originals
```

**macOS/Linux:**
```bash
cd scripts
python ingest_sales_snapshot_batch.py \
  --folder ../data/raw/Sales_snapshot_data \
  --prefix sales_snapshot \
  --upload-originals
```

> Tuỳ chọn: thêm `--individual` nếu muốn **mỗi Excel → 1 Parquet** riêng thay vì gộp.

### Kết quả mong đợi
- MinIO hiển thị đúng hai nhánh `source/` và `raw/` dưới bucket **bronze**.
- `batch_*.parquet` có đầy đủ cột như Excel (schema **không bị rút gọn**).

---

## 3) Silver layer — tạo schema & staging (dbt + Trino)
### 3.1 Tạo schema `silver.core` (Iceberg)
```sql
-- Trino CLI / Web UI
CREATE SCHEMA IF NOT EXISTS silver.core;
```

> Vì là **Iceberg**, Trino sẽ quản lý snapshot/metadata trong **Hive Metastore**. Không cần chỉ định `location` trừ khi bạn muốn custom path.

### 3.2 Đăng ký nguồn (đọc từ Parquet ở Bronze)
Có 2 cách phổ biến:

**Cách A (nhanh):** Tạo bảng **external Hive** trỏ vào `s3://bronze/raw/sales_snapshot/` rồi CTAS sang Iceberg.
1) Lấy schema cột từ Parquet (dùng sẵn script):
```bash
python scripts/check_parquet_schema.py \
  --bucket bronze \
  --key raw/sales_snapshot/batch_<timestamp>.parquet
```
2) Dùng schema in ra để **khai báo bảng Hive** (catalog `minio`) tham chiếu tới thư mục Parquet:
```sql
CREATE TABLE IF NOT EXISTS minio.default.sales_snapshot_raw (
  -- dán danh sách cột & kiểu dữ liệu ở đây (lấy từ step 1)
) WITH (
  external_location = 's3://bronze/raw/sales_snapshot/',
  format = 'PARQUET'
);
```
3) Tạo **staging Iceberg** trong `silver.core` bằng CTAS:
```sql
CREATE TABLE IF NOT EXISTS silver.core.stg_sales_snapshot
WITH (format = 'ICEBERG') AS
SELECT
  -- ép kiểu cơ bản: ngày, số, bool... (nếu cần)
  *
FROM minio.default.sales_snapshot_raw;
```

**Cách B (sạch, dùng dbt-external-tables):**
- Cài package `dbt-external-tables` và khai báo nguồn external parquet ngay trong `dbt`:
```yml
# models/sources.yml
version: 2
sources:
  - name: bronze
    schema: default          # schema trong catalog 'minio'
    tables:
      - name: sales_snapshot_raw
        external:
          location: 's3://bronze/raw/sales_snapshot/'
          options:
            format: PARQUET
```
- Sau đó tạo model `stg_sales_snapshot.sql` đọc từ nguồn này và materialize sang Iceberg:
```sql
-- models/staging/stg_sales_snapshot.sql
{{ config(materialized='table', schema='core') }}

SELECT
  -- ép kiểu, chuẩn hoá nhẹ tại đây
  *
FROM {{ source('bronze', 'sales_snapshot_raw') }}
```

> **Khuyến nghị enterprise:** Dùng **dbt** để version hoá logic, thêm **tests** và **docs**.

---

## 4) Chuẩn hoá “core” (dimension / fact)
### Ý nghĩa
- **core** = nơi đặt các bảng **chuẩn hoá** đã *conformed* schema: tách **dimension** (tra cứu) & **fact** (giao dịch).
- Giúp: dễ cập nhật, dễ kiểm thử, hỗ trợ downstream (Gold & ML).

### Ví dụ dbt models
```
models/
├── staging/
│   └── stg_sales_snapshot.sql         # từ step 3
├── core/
│   ├── dim_product.sql
│   ├── dim_region.sql
│   └── fact_sales.sql
└── marts/
    └── sales/                         # gold
        └── fct_sales_monthly.sql
```

**dim_product.sql (ví dụ):**
```sql
{{ config(materialized='table', schema='core') }}

WITH src AS (
  SELECT * FROM {{ ref('stg_sales_snapshot') }}
)
SELECT
  product_id,
  INITCAP(product_name) AS product_name,
  category,
  subcategory
FROM src
GROUP BY 1,2,3,4;
```

**fact_sales.sql (ví dụ):**
```sql
{{ config(materialized='incremental', unique_key='txn_id', schema='core') }}

WITH src AS (
  SELECT * FROM {{ ref('stg_sales_snapshot') }}
)
SELECT
  CAST(txn_id AS VARCHAR)      AS txn_id,
  CAST(order_date AS DATE)     AS order_date,
  product_id,
  region_id,
  CAST(quantity AS INTEGER)    AS quantity,
  CAST(amount   AS DOUBLE)     AS amount
FROM src
{% if is_incremental() %}
  WHERE order_date > (SELECT COALESCE(MAX(order_date), DATE '1900-01-01') FROM {{ this }})
{% endif %}
;
```

Chạy dbt:
```bash
dbt deps
dbt run --select staging+ core+
dbt test
```

---

## 5) Gold layer — tổng hợp phục vụ BI
- Tạo các model gold (marts) dạng **summary** theo tháng/tuần, KPIs.
- Ví dụ:
```sql
{{ config(materialized='table', schema='core') }}  -- hoặc schema='marts'

SELECT
  date_trunc('month', order_date) AS month,
  SUM(amount) AS revenue,
  SUM(quantity) AS qty
FROM {{ ref('fact_sales') }}
GROUP BY 1;
```
- Dùng Metabase/Superset kết nối Trino → catalog `silver` → schema `core` / `marts`.

---

## 6) Khu ML — feature store & training
- Trích xuất features từ **fact_sales** / **gold**:
  - Doanh thu rolling 7/28 ngày, growth %, anomaly scores…
- Lưu vào `feature_store/` (có thể ở `s3://ml/feature_store/` hoặc `s3://silver/feature_store/` tuỳ tách layer).
- Dùng **MLflow** hoặc lưu model artifact (pkl) vào `ml_models/`.
- Lên lịch retrain (Airflow/DAG).

---

## 7) Chính sách & vận hành (Governance)
| Layer  | Retention | Quyền truy cập | Kiểm thử |
|-------|-----------|----------------|----------|
| Bronze | Mãi mãi (immutable) | DataOps | Kiểm tra schema, checksum |
| Silver | 6–12 tháng | Data/BI team | dbt tests (not_null, unique, accepted_values) |
| Gold   | 3–6 tháng | BI/Apps | Kiểm tra KPI consistency |
| ML     | theo chu kỳ training | MLE/DS | Feature drift, model decay |

---

## 8) FAQ nhanh
- **Vì sao giữ cả Excel lẫn Parquet?**  
  Excel để **audit/replay**, Parquet để **query hiệu năng cao**.
- **Tại sao Iceberg ở Silver/Gold?**  
  Cần **ACID + snapshots + time travel** & quản lý schema tốt cho transform.
- **dbt có bắt buộc?**  
  Không, nhưng **nên dùng** để đạt chuẩn enterprise (versioning, lineage, tests).

---

## 9) Lệnh kiểm tra nhanh
```sql
-- Trino: xem schemas & tables
SHOW SCHEMAS FROM silver;
SHOW TABLES FROM silver.core;

-- Sample query
SELECT * FROM silver.core.stg_sales_snapshot LIMIT 5;
```

---

### ✅ Tóm tắt 1 câu
**Excel gốc** → vào **bronze/source**, **Parquet** → **bronze/raw** → dbt + Trino chuẩn hoá vào **silver.core (Iceberg)** → tổng hợp **gold** → xuất **features** cho **ML**.  
Từng bước đều **truy vết được**, **tự động hoá được**, và **mở rộng** dễ dàng.
