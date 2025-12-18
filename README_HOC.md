# 📚 KIẾN THỨC CẦN HỌC ĐỂ HIỂU HỆ THỐNG SME PULSE

> File này liệt kê tất cả kiến thức/khái niệm cần nắm để hiểu và phát triển hệ thống Data Lakehouse này.
> Bạn có thể copy từng mục và hỏi ChatGPT: "Giải thích cho tôi về [tên khái niệm] với ví dụ đơn giản"

---

## 1️⃣ KIẾN THỨC NỀN TẢNG (Fundamental)

### 1.1 Docker & Container
- [ ] **Docker là gì?** Container vs Virtual Machine
- [ ] **Docker Image** vs **Docker Container** 
- [ ] **docker-compose.yml**: Định nghĩa nhiều services chạy cùng lúc
- [ ] **Docker volumes**: Lưu trữ dữ liệu persistent
- [ ] **Docker networks**: Container nói chuyện với nhau như thế nào
- [ ] **Healthcheck**: Kiểm tra service có sống không

**Hỏi ChatGPT:**
```
"Giải thích Docker container là gì? Khác gì với máy ảo? Cho ví dụ đơn giản"
"docker-compose.yml dùng để làm gì? Giải thích cấu trúc cơ bản"
"Docker volume là gì? Tại sao cần volume?"
```

---

### 1.2 Database & SQL
- [ ] **PostgreSQL**: Database quan hệ (relational DB)
- [ ] **Schema**: Cách tổ chức tables trong database
- [ ] **SQL cơ bản**: SELECT, INSERT, CREATE TABLE
- [ ] **JOIN**: Kết nối nhiều bảng
- [ ] **Aggregate functions**: SUM, COUNT, AVG, GROUP BY

**Hỏi ChatGPT:**
```
"PostgreSQL là gì? Dùng để làm gì trong data engineering?"
"Schema trong database là gì? Cho ví dụ"
"Giải thích GROUP BY trong SQL với ví dụ dễ hiểu"
```

---

### 1.3 Python cơ bản
- [ ] **pandas**: Thư viện xử lý data dạng bảng
- [ ] **boto3**: Thư viện kết nối S3/MinIO
- [ ] **Functions & modules**: Import file Python khác
- [ ] **Error handling**: try/except
- [ ] **Reading files**: Excel, CSV, Parquet

**Hỏi ChatGPT:**
```
"pandas trong Python dùng để làm gì? Cho ví dụ đọc file Excel"
"boto3 là gì? Dùng để làm gì với S3?"
"File Parquet là gì? Khác gì với CSV?"
```

---

## 2️⃣ KIẾN TRÚC DATA (Data Architecture)

### 2.1 Medallion Architecture (Bronze → Silver → Gold)
- [ ] **Bronze layer**: Dữ liệu thô, immutable (không thay đổi)
- [ ] **Silver layer**: Dữ liệu đã clean, chuẩn hóa
- [ ] **Gold layer**: Dữ liệu đã aggregate, sẵn sàng cho BI
- [ ] **Tại sao chia 3 lớp?** Lợi ích của mô hình này

**Hỏi ChatGPT:**
```
"Giải thích Medallion Architecture (Bronze Silver Gold) trong data lake"
"Tại sao cần chia dữ liệu thành 3 layer? Lợi ích là gì?"
"Immutable data là gì? Tại sao Bronze phải immutable?"
```

---

### 2.2 Data Lakehouse
- [ ] **Data Lake** vs **Data Warehouse**: Khác nhau như thế nào?
- [ ] **Lakehouse**: Kết hợp ưu điểm của cả hai
- [ ] **ACID transactions**: Đảm bảo dữ liệu nhất quán
- [ ] **Schema-on-read** vs **Schema-on-write**

**Hỏi ChatGPT:**
```
"Data Lake vs Data Warehouse khác nhau như thế nào?"
"Data Lakehouse là gì? Giải quyết vấn đề gì?"
"ACID trong database là gì? Tại sao quan trọng?"
```

---

### 2.3 Object Storage (S3/MinIO)
- [ ] **Object Storage** vs **File System**: Khác nhau
- [ ] **Bucket**: Container chứa objects
- [ ] **Prefix/Path**: Tổ chức objects như folder
- [ ] **S3 API**: Giao thức chuẩn để truy cập storage

**Hỏi ChatGPT:**
```
"Object Storage là gì? Khác gì với file system thông thường?"
"MinIO là gì? Tại sao dùng MinIO thay vì AWS S3?"
"Bucket trong object storage là gì?"
```

---

## 3️⃣ CÔNG CỤ TRONG HỆ THỐNG

### 3.1 MinIO (Object Storage)
- [ ] **MinIO là gì?** S3-compatible storage
- [ ] **API endpoint**: Port 9000
- [ ] **Console**: Port 9001 (Web UI)
- [ ] **mc (MinIO Client)**: CLI tool để quản lý buckets

**Vai trò trong hệ thống:**
- Lưu trữ tất cả file Parquet (Bronze, Silver, Gold)
- Thay thế AWS S3 để chạy local

**Hỏi ChatGPT:**
```
"MinIO là gì? Dùng để làm gì trong data engineering?"
"S3-compatible nghĩa là gì?"
```

---

### 3.2 Hive Metastore
- [ ] **Metastore là gì?** Database lưu metadata
- [ ] **Metadata**: Thông tin về tables (schema, location, partitions)
- [ ] **Thrift protocol**: Giao thức để các service kết nối metastore
- [ ] **Tại sao cần Metastore?** Không thể query Parquet trực tiếp

**Vai trò trong hệ thống:**
- Lưu thông tin về tất cả tables (Bronze, Silver, Gold)
- Trino và dbt đều kết nối tới Metastore để biết table ở đâu

**Hỏi ChatGPT:**
```
"Hive Metastore là gì? Dùng để làm gì?"
"Metadata trong data engineering là gì?"
"Tại sao cần Metastore khi đã có MinIO?"
```

---

### 3.3 Trino (SQL Query Engine)
- [ ] **Trino là gì?** Distributed SQL engine
- [ ] **Catalog**: Kết nối tới data source (Iceberg, Hive, etc.)
- [ ] **Schema**: Namespace tổ chức tables
- [ ] **Connector**: Plugin kết nối nhiều loại data source
- [ ] **Distributed query**: Query chạy song song trên nhiều node

**Vai trò trong hệ thống:**
- Cho phép query dữ liệu trên MinIO bằng SQL
- dbt sử dụng Trino để chạy transformation

**Hỏi ChatGPT:**
```
"Trino (Presto) là gì? Dùng để làm gì?"
"Catalog trong Trino là gì?"
"Distributed query engine nghĩa là gì?"
```

---

### 3.4 Apache Iceberg (Table Format)
- [ ] **Table Format** là gì? Khác gì với file format?
- [ ] **Iceberg**: Modern table format hỗ trợ ACID
- [ ] **Time travel**: Xem dữ liệu ở thời điểm quá khứ
- [ ] **Schema evolution**: Thêm/xóa cột không cần rewrite data
- [ ] **Snapshot**: Mỗi lần ghi tạo một version mới

**Vai trò trong hệ thống:**
- Tất cả tables Silver và Gold dùng Iceberg
- Cho phép rollback nếu có lỗi

**Hỏi ChatGPT:**
```
"Apache Iceberg là gì? Tại sao không dùng Parquet trực tiếp?"
"Table format vs file format khác nhau như thế nào?"
"Time travel trong Iceberg là gì?"
```

---

### 3.5 dbt (Data Build Tool)
- [ ] **dbt là gì?** Tool transform data bằng SQL
- [ ] **Model**: File .sql định nghĩa một table/view
- [ ] **ref() macro**: Tham chiếu model khác
- [ ] **source() macro**: Tham chiếu raw table
- [ ] **Materialization**: table, view, incremental
- [ ] **dbt run**: Chạy tất cả models
- [ ] **dbt test**: Kiểm tra data quality

**Vai trò trong hệ thống:**
- Transform Bronze → Silver (clean data)
- Transform Silver → Gold (aggregate data)

**Hỏi ChatGPT:**
```
"dbt (data build tool) là gì? Dùng để làm gì?"
"dbt model là gì? Cho ví dụ"
"ref() và source() trong dbt khác nhau như thế nào?"
"Materialization trong dbt là gì?"
```

---

### 3.6 Airflow (Orchestration)
- [ ] **Orchestration**: Điều phối workflow tự động
- [ ] **DAG**: Directed Acyclic Graph - workflow có hướng không vòng
- [ ] **Task**: Một bước trong DAG
- [ ] **Operator**: Loại task (PythonOperator, BashOperator, etc.)
- [ ] **Scheduler**: Component chạy DAGs theo lịch
- [ ] **Webserver**: Web UI để xem và quản lý DAGs

**Vai trò trong hệ thống:**
- Chạy tự động: Ingest → dbt Silver → dbt Gold
- Schedule: Chạy hàng ngày/hàng giờ
- Retry: Tự động chạy lại nếu fail

**Hỏi ChatGPT:**
```
"Apache Airflow là gì? Dùng để làm gì?"
"DAG trong Airflow là gì? Cho ví dụ"
"Scheduler và Webserver trong Airflow khác nhau như thế nào?"
```

---

## 4️⃣ LUỒNG DỮ LIỆU (Data Flow)

### Bước 1: Ingest (Nhập dữ liệu vào Bronze)
```
Excel files (19 files)
    ↓
Python script (ops/ingest_sales_snapshot_batch.py)
    ↓
MinIO bucket: sme-pulse/bronze/raw/sales_snapshot/
    ↓
Tạo External Table trong Trino: minio.default.sales_snapshot_raw
```

**Học:**
- [ ] External table là gì? Khác gì với managed table?
- [ ] Tại sao phải tạo external table?

---

### Bước 2: Transform Bronze → Silver (dbt)
```
Bronze: minio.default.sales_snapshot_raw
    ↓
dbt model: stg_transactions.sql
    ↓
Silver: sme-pulse.silver.stg_transactions (Iceberg table)
```

**Làm gì:**
- Clean data: Convert negative values → 0
- Chuẩn hóa kiểu dữ liệu: VARCHAR, DOUBLE
- Tính toán metric: total_cost, total_revenue, gross_profit

**Học:**
- [ ] Staging table là gì?
- [ ] TRY_CAST vs CAST khác nhau gì?

---

### Bước 3: Transform Silver → Gold (dbt)
```
Silver: stg_transactions
    ↓
dbt model: fact_sales.sql
    ↓
Gold: sme-pulse.gold.fact_sales (Iceberg table)
```

**Làm gì:**
- Aggregate: GROUP BY month, site, product
- Tính tổng: SUM(qty_sold), SUM(revenue), SUM(cost)

**Học:**
- [ ] Fact table là gì?
- [ ] Grain (granularity) là gì?

---

### Bước 4: Orchestrate (Airflow)
```
Airflow DAG: sme_pulse_sales_snapshot
    ↓
Task 1: Ingest (Python script)
    ↓
Task 2: dbt Silver (dbt run --select silver)
    ↓
Task 3: dbt Gold (dbt run --select gold)
```

**Học:**
- [ ] Task dependency là gì?
- [ ] Tại sao cần orchestration?

---

## 5️⃣ CÁC FILE QUAN TRỌNG

### 5.1 docker-compose.yml
**Mục đích:** Định nghĩa tất cả services (Postgres, MinIO, Trino, Airflow, etc.)

**Học:**
- [ ] Service trong docker-compose là gì?
- [ ] depends_on: Thứ tự khởi động services
- [ ] volumes: Mount folder từ host vào container
- [ ] networks: Container cùng network nói chuyện được với nhau

---

### 5.2 dbt/dbt_project.yml
**Mục đích:** Config dbt project (model paths, materialization defaults)

**Học:**
- [ ] model-paths: Folder chứa models
- [ ] +materialized: Mặc định table hay view
- [ ] +schema: Schema đích cho models

---

### 5.3 dbt/profiles.yml
**Mục đích:** Config kết nối từ dbt tới Trino

**Học:**
- [ ] target: Environment (dev, prod)
- [ ] type: trino (dbt adapter)
- [ ] database: Catalog trong Trino
- [ ] schema: Schema mặc định

---

### 5.4 trino/catalog/sme_pulse.properties
**Mục đích:** Config Trino catalog kết nối Iceberg via Hive Metastore

**Học:**
- [ ] connector.name: Loại connector (iceberg)
- [ ] hive.metastore.uri: Địa chỉ Metastore
- [ ] s3.endpoint: Địa chỉ MinIO

---

### 5.5 hive-metastore/core-site.xml
**Mục đích:** Config Hadoop filesystem kết nối MinIO

**Học:**
- [ ] fs.s3a.endpoint: MinIO API endpoint
- [ ] fs.s3a.access.key & secret.key: Credentials

---

### 5.6 ops/ingest_sales_snapshot_batch.py
**Mục đích:** Python script đọc Excel → Parquet → upload MinIO

**Học:**
- [ ] boto3.client: Kết nối S3/MinIO
- [ ] pandas.read_excel: Đọc Excel
- [ ] to_parquet: Ghi Parquet

---

### 5.7 airflow/dags/sales_pipeline_test_dag.py
**Mục đích:** Định nghĩa DAG chạy toàn bộ pipeline

**Học:**
- [ ] @dag decorator: Tạo DAG
- [ ] PythonOperator: Chạy Python function
- [ ] Task dependencies: task1 >> task2

---

## 6️⃣ CÁC LỆNH QUAN TRỌNG

### Docker
```powershell
docker compose up -d              # Khởi động tất cả services
docker compose ps                 # Xem trạng thái services
docker compose logs -f [service]  # Xem logs
docker compose restart [service]  # Restart service
docker exec -it [container] bash  # Vào shell của container
```

### MinIO
```powershell
docker exec sme-minio mc alias set myminio http://localhost:9000 minio minio123
docker exec sme-minio mc mb myminio/bronze    # Tạo bucket
docker exec sme-minio mc ls myminio/bronze    # Liệt kê objects
```

### Trino
```powershell
docker exec -it sme-trino trino
SHOW CATALOGS;
SHOW SCHEMAS FROM "sme_pulse";
SELECT * FROM "sme_pulse".silver.stg_transactions LIMIT 10;
```

### dbt
```powershell
docker compose run --rm dbt-runner dbt debug --profiles-dir /usr/app
docker compose run --rm dbt-runner dbt run --profiles-dir /usr/app
docker compose run --rm dbt-runner dbt test --profiles-dir /usr/app
```

### Airflow
```powershell
docker exec sme-airflow-webserver airflow dags list
docker exec sme-airflow-webserver airflow dags trigger [dag_id]
docker exec sme-airflow-webserver airflow dags unpause [dag_id]
```

---

## 7️⃣ TROUBLESHOOTING (Kỹ năng Debug)

### Cách debug khi có lỗi
1. **Đọc error message** cẩn thận (thường có hint)
2. **Xem logs** của service liên quan
3. **Kiểm tra kết nối** giữa các services
4. **Verify config** (endpoint, credentials, ports)
5. **Google error message** hoặc hỏi ChatGPT

**Học:**
- [ ] Cách đọc stack trace
- [ ] Cách dùng docker logs
- [ ] Cách kiểm tra network connectivity

---

## 8️⃣ KẾ HOẠCH HỌC (Study Plan)

### Tuần 1-2: Nền tảng
1. Docker & Docker Compose
2. SQL cơ bản (SELECT, JOIN, GROUP BY)
3. Python pandas cơ bản
4. PostgreSQL cơ bản

### Tuần 3-4: Data Architecture
1. Medallion Architecture
2. Data Lake vs Warehouse vs Lakehouse
3. Object Storage (S3/MinIO)
4. Parquet file format

### Tuần 5-6: Công cụ chính
1. Trino (query engine)
2. Apache Iceberg (table format)
3. Hive Metastore
4. dbt (transformation)

### Tuần 7-8: Orchestration & Practice
1. Apache Airflow
2. Chạy thử toàn bộ pipeline
3. Debug và fix lỗi
4. Tự thêm models mới

---

## 9️⃣ TÀI LIỆU THAM KHẢO

### Documentation chính thức
- **Docker:** https://docs.docker.com/
- **Trino:** https://trino.io/docs/current/
- **dbt:** https://docs.getdbt.com/
- **Airflow:** https://airflow.apache.org/docs/
- **Iceberg:** https://iceberg.apache.org/docs/latest/
- **MinIO:** https://min.io/docs/

### Khóa học miễn phí
- Docker for Beginners (YouTube)
- SQL Tutorial (W3Schools)
- dbt Fundamentals (dbt Labs)
- Airflow Tutorial (Apache Airflow)

---

## 🎯 MỤC TIÊU CUỐI CÙNG

Sau khi học xong, bạn sẽ:
- ✅ Hiểu kiến trúc Medallion và tại sao dùng nó
- ✅ Biết cách ingest dữ liệu vào Bronze
- ✅ Viết được dbt models để transform data
- ✅ Tạo được Airflow DAG để orchestrate pipeline
- ✅ Debug được lỗi khi system fail
- ✅ Mở rộng hệ thống với tables/models mới

---

## 💡 TIPS HỌC HIỆU QUẢ

1. **Học theo thứ tự:** Nền tảng → Công cụ → Practice
2. **Làm theo tutorial:** Chạy từng bước trong SETUP_GUIDE.md
3. **Break down:** Học từng công cụ một, đừng học hết cùng lúc
4. **Hỏi ChatGPT:** Copy câu hỏi từ file này và hỏi chi tiết
5. **Practice:** Thử thêm data mới, tạo model mới
6. **Debug:** Cố tình làm lỗi rồi tự fix

---

## 📞 KHI NÀO CẦN HỎI CHATGPT?

### Ví dụ câu hỏi tốt:
```
"Giải thích Medallion Architecture với ví dụ cụ thể trong retail"
"Tại sao Iceberg tốt hơn Hive table? Cho so sánh chi tiết"
"dbt ref() macro hoạt động như thế nào? Cho ví dụ code"
"Làm sao để debug khi Airflow DAG không chạy?"
```

### Ví dụ câu hỏi không tốt:
```
"Giải thích hết tất cả mọi thứ về data engineering"  ❌
"Code giúp tôi một cái pipeline"  ❌
```

---

**Good luck! 🚀**

Bắt đầu với **Mục 1: Kiến thức nền tảng** và hỏi ChatGPT từng khái niệm một.
