## Bước 3: Silver layer — tạo schema & staging (dbt + Trino)

# SME Pulse – Hướng dẫn triển khai Bronze → Silver (Trino + dbt)

> Mục tiêu: kết nối Parquet gộp ở Bronze (trên MinIO) vào Trino (Hive external), sau đó chuẩn hoá ở Silver (Iceberg) bằng dbt. Tài liệu này viết theo Cách 1: dùng SQL thuần Trino để khai báo external table cho Bronze, và dbt để build Silver.
> 

---

## 0) Kiến trúc & vai trò từng lớp (tóm tắt)

- **Bronze (MinIO bucket `bronze`)**: dữ liệu **thô/immutable**. Ở đây ta đã gộp 19 Excel thành **một Parquet** có schema:
    
    ```
    ['month','week','site','branch_id','channel_id','distribution_channel',
     'distribution_channel_code','sold_quantity','cost_price','net_price',
     'customer_id','product_id']
    
    ```
    
- **Silver (catalog `silver`, định dạng Iceberg)**: chuẩn hoá kiểu dữ liệu, đổi tên cột, thêm kiểm tra chất lượng, tách dimension/fact.
- **Gold**: mô hình hoá cho BI/ML (không làm trong bước này).

---

## 1) Tạo external table cho Bronze trong Trino (Hive connector)

> Mục tiêu: Cho Trino “nhìn thấy” Parquet ở s3://bronze/raw/sales_snapshot/ qua catalog Hive (ví dụ minio).
> 

### 1.1. Giả định đường dẫn

- Parquet gộp nằm tại: `s3://bronze/raw/sales_snapshot/…/*.parquet`
- Nếu bạn đang dùng partition theo ngày batch thì cứ trỏ cả thư mục gốc `raw/sales_snapshot/` (Trino sẽ đọc tất cả file bên trong).

### 1.2. Lệnh SQL (chạy trong Trino CLI/Web UI)

```sql
-- 1) Kiểm tra catalog/schema hive (ví dụ catalog "minio")
SHOW SCHEMAS FROM minio; -- mong đợi thấy schema "default"

-- 2) Tạo external table trỏ vào Parquet ở Bronze
CREATE TABLE IF NOT EXISTS minio.default.sales_snapshot_raw (
    month BIGINT,
    week BIGINT,
    site BIGINT,
    branch_id BIGINT,
    channel_id VARCHAR,
    distribution_channel VARCHAR,
    distribution_channel_code VARCHAR,
    sold_quantity BIGINT,
    cost_price BIGINT,
    net_price BIGINT,
    customer_id VARCHAR,
    product_id VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://bronze/raw/sales_snapshot/'
);

-- 3) Kiểm tra nhanh
SELECT * FROM minio.default.sales_snapshot_raw LIMIT 10;

```

> Giải thích: Đây là bảng external (không ghi metadata vào MinIO ngoài file), giúp truy vấn trực tiếp Parquet thô. Không đổi kiểu dữ liệu ở đây để giữ nguyên tính "immutable" của Bronze.
> 

> Tip: Nếu bạn có subfolders (ví dụ date=YYYY-MM-DD/…), Trino vẫn đọc được khi chỉ định external_location là thư mục cha.
> 

---

## 2) Cấu hình dbt (adapter Trino) để build Silver (Iceberg)

> Mục tiêu: dbt sẽ đọc source từ minio.default.sales_snapshot_raw và ghi output sang catalog silver (Iceberg), schema core.
> 

### 2.1. `profiles.yml`

Tạo/sửa `~/.dbt/profiles.yml` (hoặc trong repo nếu bạn dùng `DBT_PROFILES_DIR`). Ví dụ:

```yaml
sme_pulse:
  target: dev
  outputs:
    dev:
      type: trino
      host: localhost
      port: 8081
      user: dbt
      threads: 4
      database: "silver"   # catalog đích (Iceberg)
      schema: "core"       # schema đích
      http_scheme: http
      session_properties:
        query_max_run_time: "5m"

```

> Giải thích: database trong dbt-trino là catalog. Ta chọn silver để mọi model sinh ra là Iceberg table dưới silver.core.
> 

### 2.2. `dbt_project.yml`

Trong root dự án dbt:

```yaml
name: "sme_pulse"
version: "1.0.0"
profile: "sme_pulse"

models:
  sme_pulse:
    +materialized: table
    +table_format: iceberg  # đảm bảo Trino ghi Iceberg
    staging:
      +schema: core
    marts:
      +schema: core

```

### 2.3. Khai báo nguồn Bronze – `models/sources.yml`

```yaml
version: 2

sources:
  - name: bronze
    description: "Bronze layer on MinIO via Hive catalog"
    database: minio      # catalog nguồn (Hive)
    schema: default      # schema nguồn
    tables:
      - name: sales_snapshot_raw
        description: "External Parquet combined from 19 Excel files"

```

> Giải thích: dbt hiểu database là catalog nguồn minio, schema là default.
> 

---

## 3) Silver/Staging: Chuẩn hoá từ Bronze

> Mục tiêu: Chuẩn hoá kiểu dữ liệu, đặt lại tên cột nhất quán, đảm bảo nullability; vẫn giữ 1–1 với bản ghi gốc (chưa aggregate). Kết quả sinh ra ở silver.core (Iceberg).
> 

### 3.1. `models/staging/stg_sales_snapshot.sql`

```sql
{{
  config(
    materialized='table',
    table_format='iceberg'
  )
}}

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
FROM cleaned;
```

> Giải thích:
> 
> - Dùng `TRY_CAST` để tránh query fail khi có giá trị bẩn.
> - Chưa ép `month/week` về kiểu date vì source có thể là chuỗi. Tuỳ nhu cầu, bạn có thể parse về `DATE`/`INT` ở đây.
> - Output là **Iceberg table** ở `silver.core.stg_sales_snapshot` → snapshot/time-travel OK.

### 3.2. Test nhanh

```bash
# Build riêng staging
.dbt\venv\Scripts\dbt run --select stg_sales_snapshot  # Windows (ví dụ)
# hoặc
poetry run dbt run --select stg_sales_snapshot          # nếu dùng Poetry

```

---

## 4) (Tuỳ chọn) Silver → Mart: fact_sales (chuẩn bị cho Gold/ML)

> Mục tiêu: Tạo bảng fact nhẹ (chưa fully kim tự tháp dữ liệu), gom theo grain phù hợp (ví dụ site–product–month). Vẫn đặt ở silver.core để nhóm ML có thể dùng trực tiếp.
> 

### 4.1. `models/marts/fact_sales.sql`

```sql
{{
  config(
    materialized='table',
    table_format='iceberg'
  )
}}

WITH base AS (
  SELECT * FROM {{ ref('stg_sales_snapshot') }}
)
SELECT
    COALESCE(month_raw,'unknown') AS month_key,
    COALESCE(site,'unknown')      AS site,
    COALESCE(product_id,'unknown') AS product_id,
    SUM(COALESCE(sold_quantity,0))           AS qty_sold,
    SUM(COALESCE(total_revenue,0))           AS revenue,
    SUM(COALESCE(total_cost,0))              AS cost,
    SUM(COALESCE(gross_profit,0))            AS gross_profit
FROM base
GROUP BY 1,2,3;

```

### 4.2. Chạy build

```bash
dbt run --select stg_sales_snapshot fact_sales

```

---

## 5) Data quality (khuyến nghị nhanh)

Tạo vài **generic tests** cho schema quan trọng:

`models/staging/schema.yml`

```yaml
version: 2

models:
  - name: stg_sales_snapshot
    columns:
      - name: product_id
        tests: [not_null]
      - name: sold_quantity
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
      - name: net_price
        tests:
          - dbt_utils.accepted_range:
              min_value: 0

```

> Cài thêm dbt-utils nếu cần.
> 

Chạy test:

```bash
dbt test --select stg_sales_snapshot

```

---

## 6) Quy ước đặt tên & phân vùng (optional nhưng nên có)

- **Tên bảng**:
    - Bronze: `minio.default.sales_snapshot_raw` (external, giữ nguyên cột)
    - Silver: `silver.core.stg_sales_snapshot` / `silver.core.fact_sales`
- **Partition**: với Iceberg, thêm partition ở model Silver nếu tần suất truy vấn theo `month_raw`/`site` là cao:
    
    ```sql
    {{
      config(
        materialized='table',
        table_format='iceberg',
        partitioned_by=['month_key']
      )
    }}
    
    ```
    

---

## 7) Lệnh tổng hợp (nhanh)

```bash
# 1) Khai báo external Bronze
# (đã ở mục 1.2, chạy trong Trino)

# 2) dbt build Silver
cd path/to/your/dbt/project

dbt debug                # kiểm tra kết nối trino

# build staging & fact
dbt run --select stg_sales_snapshot fact_sales

dbt test --select stg_sales_snapshot

```

---

## 8) FAQ ngắn

- **Vì sao không đổi kiểu dữ liệu ở Bronze?**
    
    → Bronze phải immutable. Mọi đổi kiểu/chuẩn hoá thực hiện ở Silver để dễ trace lineage.
    
- **dbt ghi ra Iceberg bằng cách nào?**
    
    → Vì `database=catalog=silver` và `+table_format: iceberg`. Trino sẽ tạo Iceberg table tại catalog đó.
    
- **Có cần `location` cho Silver schema không?**
    
    → Không bắt buộc. Trino + HMS sẽ tự quản lý đường dẫn trong bucket Silver theo config catalog. Nếu muốn tuỳ chỉnh, tạo schema kèm `location` trước rồi để dbt ghi vào.
    

---

## 9) Next steps (định hướng)

- Bổ sung **dimension tables** (dim_product, dim_branch, …) ở Silver.
- Thêm **tests**, **freshness**, và **docs** (`dbt docs generate && dbt docs serve`).
- Chuẩn bị **Gold**/semantic models cho BI/ML (feature views).
- Orchestrate bằng Airflow (chạy `dbt run` theo lịch, validate bằng `dbt test`).