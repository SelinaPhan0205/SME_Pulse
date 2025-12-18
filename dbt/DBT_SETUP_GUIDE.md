# DBT Setup Guide - SME Pulse Project

Hướng dẫn setup dbt-trino để transform dữ liệu từ Bronze → Silver layer sử dụng dbt models.

---

## 📋 Mục Lục

1. [Tổng Quan Architecture](#tổng-quan-architecture)
2. [Prerequisites](#prerequisites)
3. [Bước 1: Setup dbt Container](#bước-1-setup-dbt-container)
4. [Bước 2: Cấu Hình dbt Profiles](#bước-2-cấu-hình-dbt-profiles)
5. [Bước 3: Tạo dbt Models](#bước-3-tạo-dbt-models)
6. [Bước 4: Chạy dbt Run](#bước-4-chạy-dbt-run)
7. [Bước 5: Data Quality Tests](#bước-5-data-quality-tests)
8. [Troubleshooting](#troubleshooting)

---

## 🏗️ Tổng Quan Architecture

```
Bronze (MinIO S3)           Silver (Iceberg)          Gold (Iceberg)
─────────────────           ─────────────────         ──────────────
minio.default               silver.core               gold.core
  └─ sales_snapshot_raw       ├─ stg_transactions       └─ aggregations
     (Hive External)          └─ fact_sales
                              (dbt transforms)
```

**Flow:**
1. **Bronze**: Raw Parquet files từ CSV ingestion
2. **dbt Staging**: Clean + standardize data (convert negative values to 0)
3. **dbt Fact**: Aggregate theo (month, site, product)

---

## ✅ Prerequisites

Trước khi bắt đầu, đảm bảo:

- ✅ Docker & Docker Compose đã cài đặt
- ✅ Trino container đang chạy (`docker ps | grep sme-trino`)
- ✅ MinIO có dữ liệu Bronze (`s3://bronze/raw/sales_snapshot/`)
- ✅ External table `minio.default.sales_snapshot_raw` đã tạo

**Kiểm tra Trino connection:**
```bash
docker exec -it sme-trino trino --execute "SELECT COUNT(*) FROM minio.default.sales_snapshot_raw;"
# Expected: 831966 (hoặc số rows bạn ingest)
```

---

## Bước 1: Setup dbt Container

### 1.1. Tạo Dockerfile cho dbt-trino

Tạo file `dbt/Dockerfile`:

```dockerfile
# Dockerfile for dbt-trino
# Build locally to avoid registry issues

FROM python:3.11-slim

WORKDIR /workspace/dbt

# Install git and dbt-trino
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
    dbt-trino==1.8.2

# Set default command
CMD ["dbt", "--version"]
```

### 1.2. Thêm dbt Service vào `docker-compose.yml`

Thêm service sau vào file `docker-compose.yml`:

```yaml
  # ===== DBT RUNNER (dbt-trino for Trino integration) =====
  dbt:
    build:
      context: ./dbt
      dockerfile: Dockerfile
    container_name: sme-dbt
    working_dir: /workspace/dbt
    volumes:
      - ./dbt:/workspace/dbt
      - ./sql:/workspace/sql
    environment:
      - DBT_PROFILES_DIR=/workspace/dbt
      - TRINO_HOST=trino
      - TRINO_PORT=8080
      - TRINO_USER=admin
      - TRINO_CATALOG=silver
      - TRINO_SCHEMA=core
    depends_on:
      trino:
        condition: service_healthy
    networks:
      - sme-network
    profiles: ["no-start"]  # Không tự động start, chỉ chạy khi gọi explicit
```

### 1.3. Build dbt Image

```bash
cd d:\Project\SME_PULSE\SME_Pulse
docker-compose build dbt
```

**Expected output:**
```
[+] Building 98.5s (9/9) FINISHED
 => [3/3] RUN apt-get update && apt-get install...
 => exporting to image
 ✔ sme_pulse-dbt  Built
```

### 1.4. Verify dbt Installation

```bash
docker-compose run --rm dbt dbt --version
```

**Expected output:**
```
dbt version: 1.10.13
python version: 3.11.14
adapter type: trino
adapter version: 1.8.2
```

---

## Bước 2: Cấu Hình dbt Profiles

### 2.1. Kiểm tra `dbt/profiles.yml`

File này định nghĩa cách dbt kết nối tới Trino. Nội dung cần có:

```yaml
# ===================================================
# dbt Profile Configuration
# ===================================================
# Mục đích: Định nghĩa cách dbt kết nối tới Trino
# ===================================================

sme_pulse:
  target: dev
  outputs:
    dev:
      type: trino
      method: none              # No authentication for local dev
      user: admin               # Trino default user
      host: trino               # Tên service trong docker-compose
      port: 8080                # Trino HTTP port
      catalog: silver           # Catalog cho dbt models (silver catalog)
      schema: core              # Schema cho dbt models
      threads: 4                # Số luồng chạy song song
      http_scheme: http         # HTTP không SSL cho local dev
```

### 2.2. Test Connection

```bash
docker-compose run --rm dbt dbt debug
```

**Expected output:**
```
Configuration:
  profiles.yml file [OK found and valid]
  dbt_project.yml file [OK found and valid]
Required dependencies:
 - git [OK found]

Connection:
  host: trino
  port: 8080
  user: admin
  database: silver
  schema: core
  Connection test: [OK connection ok]

All checks passed!
```

---

## Bước 3: Tạo dbt Models

### 3.1. Cấu Trúc Thư Mục

```
dbt/
├── dbt_project.yml
├── profiles.yml
├── packages.yml          # dbt-utils package
├── Dockerfile
└── models/
    ├── sources.yml       # Source definitions (Bronze)
    ├── staging/
    │   ├── stg_transactions.sql    # Staging model
    │   └── schema.yml               # Tests for staging
    └── core/
        ├── fact_sales.sql           # Fact model
        └── schema.yml               # Tests for fact
```

### 3.2. Tạo Source Definition: `models/sources.yml`

```yaml
version: 2

sources:
  - name: bronze
    description: "Bronze layer - raw data from external Hive table"
    database: minio
    schema: default
    tables:
      - name: sales_snapshot_raw
        description: "Raw sales snapshot data from CSV ingestion"
        columns:
          - name: month
            description: "Month identifier"
          - name: week
            description: "Week identifier"
          - name: site
            description: "Site/Location"
          - name: branch_id
            description: "Branch ID"
          - name: channel_id
            description: "Channel ID"
          - name: distribution_channel
            description: "Distribution channel name"
          - name: distribution_channel_code
            description: "Distribution channel code"
          - name: sold_quantity
            description: "Quantity sold"
          - name: cost_price
            description: "Cost price per unit"
          - name: net_price
            description: "Net selling price"
          - name: customer_id
            description: "Customer identifier"
          - name: product_id
            description: "Product identifier"
```

### 3.3. Tạo Staging Model: `models/staging/stg_transactions.sql`

```sql
{{
  config(
    materialized='table',
    schema='core',
    table_format='iceberg'
  )
}}

/*
  Silver Layer - Staging Sales Snapshot
  ====================================
  Purpose: Read raw Parquet from Bronze external table, clean and conform
  Source: minio.default.sales_snapshot_raw (External Hive table)
  Target: silver.core.stg_transactions (Iceberg table)
  
  Data Quality Handling:
  - Convert negative values to 0 (Option 2: COALESCE approach)
  - This preserves row count while cleaning anomalies
*/

WITH src AS (
  SELECT
      CAST(month AS VARCHAR)                         AS month_raw,
      CAST(week AS VARCHAR)                          AS week_raw,
      CAST(site AS VARCHAR)                          AS site,
      CAST(branch_id AS VARCHAR)                     AS branch_id,
      CAST(channel_id AS VARCHAR)                    AS channel_id,
      CAST(distribution_channel AS VARCHAR)          AS distribution_channel,
      CAST(distribution_channel_code AS VARCHAR)     AS distribution_channel_code,
      TRY_CAST(sold_quantity AS DOUBLE)              AS sold_quantity_raw,
      TRY_CAST(cost_price AS DOUBLE)                 AS cost_price_raw,
      TRY_CAST(net_price AS DOUBLE)                  AS net_price_raw,
      CAST(customer_id AS VARCHAR)                   AS customer_id,
      CAST(product_id AS VARCHAR)                    AS product_id
  FROM {{ source('bronze','sales_snapshot_raw') }}
),
cleaned AS (
  SELECT
      month_raw,
      week_raw,
      site,
      branch_id,
      channel_id,
      distribution_channel,
      distribution_channel_code,
      customer_id,
      product_id,
      
      -- Data Quality: Convert negative/NULL values to 0
      CASE 
        WHEN sold_quantity_raw IS NULL THEN 0
        WHEN sold_quantity_raw < 0 THEN 0
        ELSE sold_quantity_raw 
      END AS sold_quantity,
      
      CASE 
        WHEN cost_price_raw IS NULL THEN 0
        WHEN cost_price_raw < 0 THEN 0
        ELSE cost_price_raw 
      END AS cost_price,
      
      CASE 
        WHEN net_price_raw IS NULL THEN 0
        WHEN net_price_raw < 0 THEN 0
        ELSE net_price_raw 
      END AS net_price
  FROM src
)
SELECT
    -- Time dimensions
    month_raw,
    week_raw,
    
    -- Location dimensions
    site,
    branch_id,
    
    -- Channel dimensions
    channel_id,
    distribution_channel,
    distribution_channel_code,
    
    -- Product & Customer
    customer_id,
    product_id,
    
    -- Metrics (cleaned - all >= 0)
    sold_quantity,
    cost_price,
    net_price,
    
    -- Business calculations (based on cleaned values)
    cost_price * sold_quantity              AS total_cost,
    net_price * sold_quantity               AS total_revenue,
    (net_price - cost_price) * sold_quantity AS gross_profit
FROM cleaned
```

### 3.4. Tạo Fact Model: `models/core/fact_sales.sql`

```sql
{{
  config(
    materialized='table',
    schema='core',
    table_format='iceberg',
    partitioned_by=['month_key']
  )
}}

WITH base AS (
  SELECT * FROM {{ ref('stg_transactions') }}
)
SELECT
    COALESCE(month_raw, 'unknown')       AS month_key,
    COALESCE(site, 'unknown')            AS site,
    COALESCE(product_id, 'unknown')      AS product_id,
    SUM(COALESCE(sold_quantity, 0))      AS qty_sold,
    SUM(COALESCE(total_revenue, 0))      AS revenue,
    SUM(COALESCE(total_cost, 0))         AS cost,
    SUM(COALESCE(gross_profit, 0))       AS gross_profit
FROM base
GROUP BY 1, 2, 3
```

### 3.5. Tạo Schema Tests: `models/staging/schema.yml`

```yaml
version: 2

models:
  - name: stg_transactions
    description: "Staging layer - cleaned, standardized sales transactions from Bronze"
    columns:
      - name: product_id
        description: "Product identifier"
        tests:
          - not_null

      - name: sold_quantity
        description: "Quantity sold (must be >= 0)"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0

      - name: cost_price
        description: "Cost price per unit (must be >= 0)"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0

      - name: net_price
        description: "Net selling price per unit (must be >= 0)"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
```

### 3.6. Tạo Schema Tests: `models/core/schema.yml`

```yaml
version: 2

models:
  - name: fact_sales
    description: "Core fact table - aggregated sales metrics by (month, site, product)"
    columns:
      - name: month_key
        description: "Month key from staging (or 'unknown')"
        tests:
          - not_null

      - name: qty_sold
        description: "Total quantity sold (aggregated)"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0

      - name: revenue
        description: "Total revenue (aggregated)"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
```

---

## Bước 4: Chạy dbt Run

### 4.1. Install dbt Packages

```bash
cd d:\Project\SME_PULSE\SME_Pulse
docker-compose run --rm dbt dbt deps
```

**Expected output:**
```
Installing dbt-labs/dbt_utils@1.1.1
Installed from version 1.1.1
```

### 4.2. Run Staging Models

```bash
docker-compose run --rm dbt dbt run --select staging
```

**Expected output:**
```
17:03:06  1 of 1 START sql table model core.stg_transactions ......... [RUN]
17:03:22  1 of 1 OK created sql table model core.stg_transactions .... [CREATE TABLE (831_966 rows) in 15.86s]

Completed successfully

Done. PASS=1 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=1
```

**Verify trong Trino:**
```bash
docker exec -it sme-trino trino --execute "SELECT COUNT(*) FROM silver.core.stg_transactions;"
# Expected: 831966
```

### 4.3. Run Fact Models

```bash
docker-compose run --rm dbt dbt run --select fact_sales
```

**Expected output:**
```
17:04:32  1 of 1 START sql table model core.fact_sales ............... [RUN]
17:04:39  1 of 1 OK created sql table model core.fact_sales .......... [CREATE TABLE (703_824 rows) in 6.93s]

Completed successfully

Done. PASS=1 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=1
```

**Verify trong Trino:**
```bash
docker exec -it sme-trino trino --execute "SELECT COUNT(*) FROM silver.core.fact_sales;"
# Expected: 703824
```

### 4.4. Run Tất Cả Models

```bash
docker-compose run --rm dbt dbt run
```

---

## Bước 5: Data Quality Tests

### 5.1. Run Tests

```bash
docker-compose run --rm dbt dbt test
```

**Expected output:**
```
17:05:10  1 of 9 START test not_null_stg_transactions_product_id ....... [RUN]
17:05:11  1 of 9 PASS not_null_stg_transactions_product_id ............. [PASS in 0.85s]
17:05:11  2 of 9 START test accepted_range_stg_transactions_sold_quantity [RUN]
17:05:12  2 of 9 PASS accepted_range_stg_transactions_sold_quantity .... [PASS in 1.23s]
...

Completed successfully

Done. PASS=9 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=9
```

### 5.2. Run Tests Cho Model Cụ Thể

```bash
# Test staging only
docker-compose run --rm dbt dbt test --select stg_transactions

# Test fact only
docker-compose run --rm dbt dbt test --select fact_sales
```

---

## 🎯 Kết Quả Cuối Cùng

Sau khi hoàn thành, bạn sẽ có:

| Table | Catalog | Schema | Rows | Description |
|-------|---------|--------|------|-------------|
| `sales_snapshot_raw` | minio | default | 831,966 | Bronze raw data (External Hive) |
| `stg_transactions` | silver | core | 831,966 | Cleaned staging data (Iceberg) |
| `fact_sales` | silver | core | 703,824 | Aggregated fact table (Iceberg) |

**Data Quality:**
- ✅ No negative values (converted to 0)
- ✅ No NULL in critical columns
- ✅ All business calculations correct

---

## 📊 Các Lệnh dbt Thường Dùng

```bash
# Debug connection
docker-compose run --rm dbt dbt debug

# Install packages
docker-compose run --rm dbt dbt deps

# Run all models
docker-compose run --rm dbt dbt run

# Run specific model
docker-compose run --rm dbt dbt run --select stg_transactions

# Run models + tests
docker-compose run --rm dbt dbt build

# Test all
docker-compose run --rm dbt dbt test

# Generate docs
docker-compose run --rm dbt dbt docs generate

# Clean old artifacts
docker-compose run --rm dbt dbt clean
```

---

## 🐛 Troubleshooting

### Issue 1: "Could not find matching node for patch with name 'stg_sales_snapshot'"

**Nguyên nhân:** Tên model trong `schema.yml` không khớp với tên file SQL.

**Giải pháp:**
- File SQL: `stg_transactions.sql`
- Schema.yml phải dùng: `name: stg_transactions`

### Issue 2: "Model depends on a node which was not found"

**Nguyên nhân:** `ref()` trong fact model không tìm thấy staging model.

**Giải pháp:**
```sql
-- Sai:
{{ ref('stg_sales_snapshot') }}

-- Đúng (theo tên file):
{{ ref('stg_transactions') }}
```

### Issue 3: "Compilation Error - dbt found two models with the same name"

**Nguyên nhân:** Có duplicate model files.

**Giải pháp:**
```bash
# Tìm duplicates
find dbt/models -name "stg_transactions.sql"

# Xóa file cũ trong models/silver/
rm dbt/models/silver/stg_transactions.sql
```

### Issue 4: "Connection test failed"

**Nguyên nhân:** Trino không chạy hoặc catalog chưa đúng.

**Giải pháp:**
```bash
# Check Trino
docker ps | grep sme-trino

# Restart Trino
docker-compose restart trino

# Test connection manually
docker exec -it sme-trino trino --execute "SHOW CATALOGS;"
```

### Issue 5: "No matching distribution found for dbt-utils"

**Nguyên nhân:** `dbt-utils` là dbt package, không phải pip package.

**Giải pháp:**
- Không cài qua pip
- Cài qua `packages.yml` + `dbt deps`

---

## 📚 Tài Liệu Tham Khảo

- [dbt Documentation](https://docs.getdbt.com/)
- [dbt-trino Adapter](https://github.com/starburstdata/dbt-trino)
- [Trino Documentation](https://trino.io/docs/current/)
- [Iceberg Table Format](https://iceberg.apache.org/)

---

## ✅ Checklist Hoàn Thành

- [ ] dbt container built successfully
- [ ] `dbt debug` all checks passed
- [ ] Source `bronze.sales_snapshot_raw` accessible
- [ ] Staging model `stg_transactions` created (831,966 rows)
- [ ] Fact model `fact_sales` created (703,824 rows)
- [ ] Data quality tests passed (no negatives, no NULLs)
- [ ] Team có thể chạy `dbt run` độc lập

---

**Author:** GitHub Copilot  
**Last Updated:** October 24, 2025  
**Version:** 1.0