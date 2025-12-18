# 🚀 KIẾN TRÚC AIRFLOW - DỰ ÁN SME PULSE

## 📋 MỤC ĐÍCH TÀI LIỆU

Tài liệu này mô tả **kiến trúc hoàn chỉnh** của hệ thống Airflow DAGs cho Data Pipeline dự án SME Pulse, bao gồm:
- Tổng quan 3 DAGs và vai trò của từng DAG
- Luồng xử lý dữ liệu chi tiết (Bronze → Silver → Gold)
- Cấu trúc code và các phụ thuộc
- Lịch chạy tự động & chiến lược giám sát
- Tích hợp với Metabase & Redis

---

## 🏗️ TỔNG QUAN KIẾN TRÚC

### **3 DAGs trong hệ thống:**

```
┌─────────────────────────────────────────────────────────────────┐
│  DAG 1: sme_pulse_daily_etl (CHÍNH - CHẠY HÀNG NGÀY)           │
│  ├─ Lịch chạy: Hàng ngày lúc 2:00 sáng UTC (9:00 sáng VN)      │
│  ├─ Mục đích: Pipeline chính xử lý dữ liệu vận hành             │
│  └─ Thời gian: ~15-20 phút                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         Đọc 3 file CSV → Chuyển đổi → Phục vụ BI Dashboard
                              
┌─────────────────────────────────────────────────────────────────┐
│  DAG 2: sme_pulse_external_data_sync (DỮ LIỆU THAM CHIẾU)      │
│  ├─ Lịch chạy: Hàng tháng, ngày 1 lúc 00:00 UTC                │
│  ├─ Mục đích: Đồng bộ dữ liệu kinh tế vĩ mô từ API ngoài       │
│  └─ Thời gian: ~5 phút                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         API World Bank + API Tỉnh thành VN → dbt external models

┌─────────────────────────────────────────────────────────────────┐
│  DAG 3: sme_pulse_data_quality_monitor (GIÁM SÁT CHẤT LƯỢNG)   │
│  ├─ Lịch chạy: Mỗi giờ                                          │
│  ├─ Mục đích: Kiểm tra chất lượng dữ liệu liên tục & cảnh báo  │
│  └─ Thời gian: ~2 phút                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         Giám sát metrics → Cảnh báo khi phát hiện bất thường
```

---

## 📊 DAG 1: `sme_pulse_daily_etl` (PIPELINE CHÍNH)

### **Thông tin DAG:**
```yaml
Mã DAG: sme_pulse_daily_etl
Mô tả: "Pipeline hàng ngày từ đầu đến cuối: CSV → Bronze → Silver → Gold → BI"
Lịch chạy: "0 2 * * *"  # Hàng ngày 2:00 sáng UTC (9:00 sáng Việt Nam)
Catchup: false  # Không chạy lại các lần chạy đã bỏ lỡ
Số lần chạy đồng thời tối đa: 1
Tham số mặc định:
  owner: data-engineering
  depends_on_past: false  # Không phụ thuộc vào lần chạy trước
  retries: 2  # Thử lại tối đa 2 lần khi lỗi
  retry_delay: 5 phút
  execution_timeout: 30 phút
Tags: ['production', 'daily', 'etl']
```

---

### **SƠ ĐỒ LUỒNG TASKS:**

```
verify_infrastructure (Kiểm tra hạ tầng)
    ↓
┌─────────────────────────────────────────┐
│  BRONZE INGESTION (Nhóm tasks đọc dữ liệu thô) │
│  ├─ ingest_bank_transactions            │  (Chạy song song)
│  ├─ ingest_shipments_payments           │  (Chạy song song)
│  └─ ingest_sales_snapshot               │  (Chạy song song)
└─────────────────────────────────────────┘
    ↓
bronze_validation (Kiểm tra dữ liệu Bronze)
    ↓
dbt_seed_check_and_load (Load dữ liệu seeds nếu có thay đổi)
    ↓
┌─────────────────────────────────────────┐
│  SILVER LAYER (Lớp dữ liệu staging)     │
│  ├─ dbt_silver_staging                  │
│  └─ dbt_silver_test                     │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  GOLD DIMENSIONS (Bảng chiều)           │
│  ├─ dbt_gold_dims                       │  (Chạy song song)
│  └─ dbt_gold_dims_test                  │  (Chạy song song)
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  GOLD FACTS (Bảng sự kiện)              │
│  ├─ dbt_gold_facts                      │  (Chạy song song)
│  └─ dbt_gold_facts_test                 │  (Chạy song song)
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  GOLD LINKS (Bảng liên kết)             │
│  ├─ dbt_gold_links                      │  (Chạy song song)
│  └─ dbt_gold_links_test                 │  (Chạy song song)
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  SERVE LAYER (Phục vụ BI)               │
│  ├─ metabase_refresh_cache              │  (Chạy song song)
│  └─ redis_invalidate_cache              │  (Chạy song song)
└─────────────────────────────────────────┘
    ↓
generate_pipeline_report (Tạo báo cáo)
    ↓
notify_completion (Gửi thông báo hoàn tất)
```

---

### **CHI TIẾT CÁC TASKS:**

#### **1. verify_infrastructure** (Task kiểm tra hạ tầng - PythonOperator)
**Mục đích:** Kiểm tra sức khỏe toàn bộ hạ tầng hệ thống trước khi chạy pipeline

**Các kiểm tra thực hiện:**
- ✅ MinIO có hoạt động không? (localhost:9000)
- ✅ Trino coordinator có phản hồi không? (localhost:8080)
- ✅ Kết nối Postgres (Metabase DB) OK?
- ✅ Redis cache service đang chạy?
- ✅ File cấu hình dbt profiles.yml hợp lệ?

**Kết quả trả về:** Dict trạng thái qua XCom
```python
{
    "minio_status": "healthy",
    "trino_status": "healthy",
    "postgres_status": "healthy",
    "redis_status": "healthy",
    "dbt_status": "healthy",
    "timestamp": "2025-11-03T02:00:05Z"
}
```

**Khi thất bại:** Bỏ qua pipeline, gửi cảnh báo

---

#### **2. BRONZE INGESTION TaskGroup** (Nhóm tasks đọc dữ liệu - chạy song song)

##### **Task 2.1: ingest_bank_transactions** (Đọc giao dịch ngân hàng)
**Script Python:** `/opt/ops/ingest_bank_transactions.py`

**Quy trình xử lý:**
1. Đọc file `/opt/data/source/Bank-Transactions.csv`
2. Kiểm tra cấu trúc bảng (các cột: bookg_dt_tm_gmt, ccy, dr_cr, amount, ...)
3. Chuyển đổi sang định dạng Parquet với kiểu dữ liệu đúng:
   - bookg_dt_tm_gmt → TIMESTAMP (thời gian giao dịch)
   - amount → DOUBLE (số tiền)
   - csvbase_row_id → BIGINT (ID dòng)
4. Upload lên MinIO:
   - Bucket: `sme-lake`
   - Đường dẫn: `bronze/raw/bank_transactions/bank_txn_raw.parquet`
5. Ghi log số dòng & kích thước file

**Chỉ số thành công:**
- Số dòng: ~105,000+
- Kích thước: ~2-3 MB
- Thời gian upload: <30 giây

---

##### **Task 2.2: ingest_shipments_payments** (Đọc dữ liệu vận chuyển & thanh toán)
**Script Python:** `/opt/ops/ingest_shipments_payments.py`

**Quy trình xử lý:**
1. Đọc file `/opt/data/source/shipments_payments.csv`
2. Kiểm tra cấu trúc (dự kiến 302K dòng)
3. Chuyển đổi sang Parquet:
   - Transaction_ID → VARCHAR (mã giao dịch)
   - Amount → DOUBLE (số tiền)
   - Order Date/Time → TIMESTAMP (thời gian đặt hàng)
4. Upload lên MinIO:
   - Đường dẫn: `bronze/raw/shipments_payments/shipments_payments_raw.parquet`
5. Ghi log thống kê

**Chỉ số thành công:**
- Số dòng: ~302,000+
- Kích thước: ~8-10 MB
- Thời gian upload: <60 giây

---

##### **Task 2.3: ingest_sales_snapshot** (Đọc snapshot doanh số)
**Script Python:** `/opt/ops/ingest_batch_snapshot.py`

**Quy trình xử lý:**
1. Đọc file `/opt/data/source/sales_snapshot.xlsx` (định dạng Excel)
2. Chuyển đổi XLSX → Parquet:
   - Xử lý định dạng ngày tháng Excel
   - Làm sạch tên cột (xóa khoảng trắng)
   - Chuyển đổi kiểu dữ liệu đúng
3. Upload lên MinIO:
   - Đường dẫn: `bronze/raw/sales_snapshot/sales_snapshot_raw.parquet`
4. Ghi log số dòng

**Chỉ số thành công:**
- Số dòng: ~1,663,932
- Kích thước: ~30-40 MB
- Thời gian upload: <90 giây

**Xử lý đặc biệt:**
- File lớn → Dùng chunking nếu thiếu RAM
- Công thức Excel → Tính toán ra giá trị cụ thể

---

#### **3. bronze_validation** (Kiểm tra chất lượng dữ liệu Bronze)
**Mục đích:** Xác minh chất lượng dữ liệu lớp Bronze trước khi tiếp tục

**Các kiểm tra:**
1. **Kiểm tra số dòng:**
   ```sql
   SELECT COUNT(*) FROM minio.default.bank_txn_raw;  -- Mong đợi: 105K+
   SELECT COUNT(*) FROM minio.default.shipments_payments_raw;  -- Mong đợi: 302K+
   SELECT COUNT(*) FROM minio.default.sales_snapshot_raw;  -- Mong đợi: 1.66M+
   ```

2. **Kiểm tra cấu trúc bảng:**
   - Tất cả cột dự kiến có tồn tại không?
   - Kiểu dữ liệu có đúng không?

3. **Kiểm tra giá trị NULL:**
   - Các cột quan trọng (IDs, dates) có < 5% null?

4. **Kiểm tra khoảng thời gian:**
   - Dữ liệu nằm trong khoảng dự kiến (2022-2026)?

**Khi thất bại:** 
- Nếu kiểm tra không qua → Bỏ qua các tasks phía sau
- Gửi cảnh báo kèm báo cáo validation

---

#### **4. dbt_seed_check_and_load** (Kiểm tra và load dữ liệu seeds)
**Mục đích:** Chỉ load seed files khi có thay đổi (tối ưu hiệu suất)

**Logic xử lý:**
```python
# Mã giả
def check_seeds_changed():
    current_hash = hash_directory('/opt/dbt/seeds/')  # Hash thư mục seeds hiện tại
    previous_hash = Variable.get('last_seed_hash', default=None)  # Hash lần trước
    
    if current_hash != previous_hash:
        run_dbt_seed()  # Chạy dbt seed
        Variable.set('last_seed_hash', current_hash)  # Lưu hash mới
        return True  # Tiếp tục
    else:
        return False  # Bỏ qua dbt seed (không có thay đổi)
```

**Lệnh dbt:**
```bash
docker compose exec dbt dbt seed
```

**Các file Seeds được load:**
- seed_channel_map (5 dòng - kênh bán hàng)
- seed_payment_method_map (4 dòng - phương thức thanh toán)
- seed_carrier_map (4 dòng - đơn vị vận chuyển)
- seed_fx_rates (12 dòng - tỷ giá ngoại tệ)
- seed_vietnam_locations (691 dòng - tỉnh thành VN)
- seed_vn_holidays (45 dòng - ngày lễ VN)

**Thời gian:** ~5 giây (nếu có thay đổi)

---

#### **5. SILVER LAYER TaskGroup** (Nhóm tasks lớp Silver - Staging)

##### **Task 5.1: dbt_silver_staging** (Xây dựng các bảng staging)
**Lệnh:**
```bash
docker compose exec dbt dbt run --select silver.* --exclude silver.external.*
```

**Các models được tạo:**
- `stg_orders_vn` (1.66M dòng - đơn hàng bán buôn)
- `stg_payments_vn` (375K dòng - thanh toán bán lẻ)
- `stg_shipments_vn` (302K dòng - vận chuyển)
- `stg_bank_txn_vn` (206K dòng - giao dịch ngân hàng)
- `stg_vietnam_locations` (691 dòng - tỉnh thành VN)
- `stg_wb_indicators` (30 dòng - chỉ số World Bank) - Loại trừ nếu dùng --exclude external

**Thời gian:** ~30-40 giây

**Cách tạo bảng:** Tất cả dùng `table` (idempotent - refresh toàn bộ mỗi lần chạy)

---

##### **Task 5.2: dbt_silver_test** (Kiểm tra chất lượng Silver)
**Lệnh:**
```bash
docker compose exec dbt dbt test --select silver.*
```

**Các test chạy:**
- Ràng buộc duy nhất (IDs, natural keys)
- Kiểm tra NOT NULL (các cột bắt buộc)
- Tính toàn vẹn tham chiếu (foreign keys tới seeds)
- Giá trị hợp lệ (mã trạng thái, danh mục)
- Các test chất lượng tùy chỉnh

**Thời gian:** ~10-15 giây

**Khi test fail:** Ghi log lỗi, không chặn pipeline (chỉ cảnh báo)

---

#### **6. GOLD DIMENSIONS TaskGroup** (Nhóm tasks lớp Gold - Dimensions)

##### **Task 6.1: dbt_gold_dims** (Xây dựng các bảng chiều)
**Lệnh:**
```bash
docker compose exec dbt dbt run --select gold.dims.* gold.external.dim_*
```

**Các models được tạo (8 bảng Dimension):**
- `dim_date` (1,826 dòng - Lịch 2022-2026 có ngày lễ VN)
- `dim_customer` (87,939 dòng - Danh sách khách hàng với SCD Type 2)
- `dim_product` (30,685 dòng - Danh sách sản phẩm với SCD Type 1)
- `dim_channel` (5 dòng - Kênh bán hàng từ seeds)
- `dim_payment_method` (4 dòng - Phương thức thanh toán từ seeds)
- `dim_carrier` (4 dòng - Đơn vị vận chuyển từ seeds)
- `dim_location` (691 dòng - Tỉnh/huyện/xã Việt Nam)
- `dim_macro_indicators` (10 dòng - Chỉ số kinh tế vĩ mô World Bank)

**Thời gian:** ~10-15 giây (chạy song song)

---

##### **Task 6.2: dbt_gold_dims_test** (Kiểm tra Dimensions)
**Các test chạy:**
- Tính duy nhất của surrogate keys
- Logic SCD Type 2 (valid_from < valid_to)
- Tính đầy đủ của dữ liệu tham chiếu

**Thời gian:** ~5 giây

---

#### **7. GOLD FACTS TaskGroup** (Nhóm tasks lớp Gold - Facts)

##### **Task 7.1: dbt_gold_facts** (Xây dựng các bảng sự kiện)
**Lệnh:**
```bash
docker compose exec dbt dbt run --select gold.facts.*
```

**Các models được tạo (4 bảng Fact):**
- `fact_orders` (1.66M dòng - Đơn hàng bán buôn B2B)
- `fact_payments` (375K dòng - Thanh toán bán lẻ B2C)
- `fact_shipments` (302K dòng - Dữ liệu vận chuyển)
- `fact_bank_txn` (206K dòng - Giao dịch ngân hàng)

**Thời gian:** ~40-50 giây (bảng lớn)

---

##### **Task 7.2: dbt_gold_facts_test** (Kiểm tra Facts)
**Các test chạy:**
- Tính toàn vẹn foreign keys (fact → dims)
- Tính nhất quán số đo (amount > 0)
- Xác thực khoảng ngày
- Tính duy nhất của grain

**Thời gian:** ~15 giây

---

#### **8. GOLD LINKS TaskGroup** (Nhóm tasks lớp Gold - Links)

##### **Task 8.1: dbt_gold_links** (Xây dựng bảng liên kết)
**Lệnh:**
```bash
docker compose exec dbt dbt run --select gold.links.*
```

**Các models được tạo (2 bảng Link):**
- `link_payment_shipment` (0 dòng - dữ liệu demo)
- `link_order_payment` (0 dòng - dữ liệu demo)

**Thời gian:** ~5 giây

**Lưu ý:** Bảng links trống trong dữ liệu demo - giữ lại cho production khi có dữ liệu thật

---

##### **Task 8.2: dbt_gold_links_test** (Kiểm tra Links)
**Các test chạy:**
- Ngưỡng điểm khớp (match scores)
- Logic chọn khớp tốt nhất (best match)

**Thời gian:** ~2 giây

---

#### **9. SERVE LAYER TaskGroup** (Nhóm tasks lớp Phục vụ - Serving)

##### **Task 9.1: metabase_refresh_cache** (Làm mới cache Metabase)
**Mục đích:** Xóa cache Metabase để làm mới dashboards

**Phương án 1: Gọi API**
```python
POST http://localhost:3000/api/database/{db_id}/sync_schema
Headers:
    X-Metabase-Session: {session_token}
```

**Phương án 2: Xóa Redis Cache**
```python
redis_client.delete('metabase:cache:*')
```

**Thời gian:** ~5 giây

---

##### **Task 9.2: redis_invalidate_cache** (Xóa cache ứng dụng)
**Mục đích:** Xóa các cache keys của ứng dụng

```python
# Các patterns cần xóa
redis_client.delete_pattern('sme:gold:fact_*')
redis_client.delete_pattern('sme:gold:dim_*')
redis_client.delete_pattern('sme:aggregates:*')
```

**Thời gian:** ~1 giây

---

#### **10. generate_pipeline_report** (Tạo báo cáo pipeline)
**Mục đích:** Tạo báo cáo thống kê chạy pipeline

**Nội dung báo cáo:**
```json
{
  "pipeline_id": "sme_pulse_daily_etl",
  "execution_date": "2025-11-03T02:00:00Z",
  "total_duration_seconds": 850,
  "bronze_ingestion": {
    "bank_txn": {"rows": 105557, "size_mb": 2.3, "duration_sec": 25},
    "shipments_payments": {"rows": 302010, "size_mb": 9.1, "duration_sec": 45},
    "sales_snapshot": {"rows": 1663932, "size_mb": 38.2, "duration_sec": 85}
  },
  "silver_layer": {
    "models_built": 6,
    "total_rows": 2548628,
    "duration_sec": 42,
    "tests_passed": 28,
    "tests_failed": 0
  },
  "gold_layer": {
    "dimensions": {"count": 8, "total_rows": 121155},
    "facts": {"count": 4, "total_rows": 2548628},
    "links": {"count": 2, "total_rows": 0},
    "duration_sec": 65,
    "tests_passed": 42,
    "tests_failed": 0
  },
  "data_quality_score": 98.5,
  "status": "SUCCESS"
}
```

**Lưu trữ báo cáo:** 
- XCom (ngắn hạn - trong phiên chạy)
- Bảng audit PostgreSQL (dài hạn - lưu lịch sử)

**Thời gian:** ~2 giây

---

#### **11. notify_completion** (Gửi thông báo hoàn thành)
**Mục đích:** Gửi thông báo kết quả chạy pipeline

**Các kênh thông báo:**
1. **Slack:**
   ```
   ✅ SME Pulse Pipeline Hàng Ngày - THÀNH CÔNG
   
   📊 Tóm tắt:
   - Bronze: 2.5M dòng được tải lên
   - Silver: 6 models đã xây dựng
   - Gold: 12 models đã xây dựng (8 dims + 4 facts)
   - Thời gian chạy: 14 phút 10 giây
   - Điểm Chất Lượng Dữ Liệu: 98.5%
   
   🔗 Metabase: http://localhost:3000
   📈 Airflow: http://localhost:8081
   ```

2. **Email:** (chỉ khi có lỗi)
   - To: data-engineering@company.com
   - Subject: "[LỖI] SME Pulse Pipeline Hàng Ngày"
   - Attachment: Error logs

**Điều kiện kích hoạt:**
- Thành công: Thông báo Slack
- Lỗi: Slack + Email + PagerDuty (môi trường production)

**Thời gian:** ~1 giây

---

## 📊 DAG 2: `sme_pulse_external_data_sync`

### **Metadata:**
```yaml
DAG ID: sme_pulse_external_data_sync
Description: "Đồng bộ hàng tháng dữ liệu tham chiếu bên ngoài (World Bank + Tỉnh thành VN)"
Schedule: "0 0 1 * *"  # Ngày 1 mỗi tháng, 00:00 UTC (7:00 sáng VN)
Catchup: false
Max Active Runs: 1
Default Args:
  owner: data-engineering
  retries: 3
  retry_delay: 10 phút
Tags: ['production', 'monthly', 'external']
```

---

### **SƠ ĐỒ TASKS:**

```
verify_external_apis (Kiểm tra APIs)
    ↓
check_data_freshness (Kiểm tra độ mới của dữ liệu)
    ↓
┌─────────────────────────────────────────┐
│  API INGESTION (Chạy song song)         │
│  ├─ ingest_world_bank_indicators        │
│  └─ ingest_vietnam_provinces            │
└─────────────────────────────────────────┘
    ↓
dbt_silver_external (Xây dựng Silver external)
    ↓
dbt_gold_external (Xây dựng Gold external)
    ↓
dbt_test_external (Kiểm tra external)
    ↓
log_external_sync_summary (Ghi log tóm tắt)
```

---

### **CHI TIẾT CÁC TASKS:**

#### **1. verify_external_apis** (Kiểm tra tính khả dụng của APIs)
**Các APIs kiểm tra:**
- ✅ World Bank API: https://api.worldbank.org/v2/country/VNM/indicator/
- ✅ Vietnam Provinces API: https://provinces.open-api.vn/api/

**Timeout:** 30 giây mỗi API

---

#### **2. check_data_freshness** (Kiểm tra dữ liệu có cần cập nhật không)
**Logic xử lý:**
```python
last_sync = Variable.get('external_data_last_sync')
days_since_sync = (datetime.now() - last_sync).days

if days_since_sync < 30:
    return False  # Bỏ qua pipeline (dữ liệu còn mới)
else:
    return True  # Tiếp tục (dữ liệu cũ, cần cập nhật)
```

---

#### **3. ingest_world_bank_indicators** (Tải dữ liệu World Bank)
**Script:** `/opt/ops/external_sources/ingest_world_bank.py`

**Các chỉ số tải về:**
- FP.CPI.TOTL.ZG (Lạm phát)
- NY.GDP.MKTP.KD.ZG (Tăng trưởng GDP)
- SL.UEM.TOTL.ZS (Thất nghiệp)

**Khoảng thời gian:** 2015-2024 (10 năm)

**Kết quả:** 30 dòng (3 chỉ số × 10 năm)

---

#### **4. ingest_vietnam_provinces** (Tải dữ liệu tỉnh thành VN)
**Script:** `/opt/ops/external_sources/ingest_provinces.py`

**Dữ liệu tải về:**
- Tỉnh/Thành phố (63)
- Quận/Huyện (691)
- Phường/Xã (10,599) - Tùy chọn

**Kết quả:** 691 bản ghi quận/huyện

---

#### **5. dbt_silver_external** (Xây dựng Silver external)
```bash
dbt run --select silver.external.*
```

**Models được tạo:**
- stg_wb_indicators (30 dòng)
- stg_vietnam_locations (691 dòng)

---

#### **6. dbt_gold_external** (Xây dựng Gold external)
```bash
dbt run --select gold.external.*
```

**Models được tạo:**
- dim_macro_indicators (10 dòng)
- dim_location (691 dòng)

---

#### **7. dbt_test_external** (Kiểm tra external)
```bash
dbt test --select external.*
```

---

#### **8. log_external_sync_summary** (Ghi log tóm tắt đồng bộ)
**Cập nhật Airflow Variables:**
```python
Variable.set('external_data_last_sync', datetime.now())
Variable.set('wb_indicators_count', 30)
Variable.set('provinces_count', 691)
```

---

## 📊 DAG 3: `sme_pulse_data_quality_monitor`

### **Metadata:**
```yaml
DAG ID: sme_pulse_data_quality_monitor
Description: "Kiểm tra chất lượng dữ liệu hàng giờ và phát hiện bất thường"
Schedule: "0 * * * *"  # Mỗi giờ
Catchup: false
Max Active Runs: 1
Default Args:
  owner: data-engineering
  retries: 1
Tags: ['monitoring', 'hourly', 'data-quality']
```

---

### **SƠ ĐỒ TASKS:**

```
┌─────────────────────────────────────────┐
│  DATA QUALITY CHECKS (Parallel)         │
│  ├─ check_row_counts                    │
│  ├─ check_data_freshness                │
│  ├─ check_null_percentages              │
│  └─ check_duplicate_keys                │
└─────────────────────────────────────────┘
    ↓
aggregate_quality_metrics
    ↓
alert_on_anomalies (ShortCircuitOperator)
    ↓
send_alerts (SlackOperator)
```

---

### **CHI TIẾT CÁC TASKS:**

#### **1. check_row_counts** (Kiểm tra số lượng dòng)
**Truy vấn SQL:**
```sql
SELECT 
    'fact_orders' as table_name,
    COUNT(*) as current_count,
    1663932 as expected_count,
    ABS(COUNT(*) - 1663932) / 1663932.0 as variance_pct
FROM sme_lake.gold.fact_orders;

-- Lặp lại cho tất cả bảng fact
```

**Ngưỡng cảnh báo:** variance > 10%

---

#### **2. check_data_freshness** (Kiểm tra độ mới của dữ liệu)
**Kiểm tra:**
```sql
SELECT 
    MAX(order_date) as latest_date,
    DATEDIFF('day', MAX(order_date), CURRENT_DATE) as days_old
FROM sme_lake.gold.fact_orders;
```

**Ngưỡng cảnh báo:** days_old > 2 (dữ liệu cũ quá 2 ngày)

---

#### **3. check_null_percentages** (Kiểm tra tỷ lệ NULL)
**Kiểm tra các cột quan trọng:**
```sql
SELECT 
    'fact_orders' as table_name,
    'customer_key' as column_name,
    COUNT(*) FILTER (WHERE customer_key IS NULL) * 100.0 / COUNT(*) as null_pct
FROM sme_lake.gold.fact_orders;
```

**Ngưỡng cảnh báo:** null_pct > 5%

---

#### **4. check_duplicate_keys** (Kiểm tra trùng lặp keys)
**Kiểm tra:**
```sql
SELECT 
    customer_key,
    COUNT(*) as duplicate_count
FROM sme_lake.gold.dim_customer
WHERE is_current = TRUE
GROUP BY customer_key
HAVING COUNT(*) > 1;
```

**Ngưỡng cảnh báo:** bất kỳ trùng lặp nào được tìm thấy

---

#### **5. aggregate_quality_metrics** (Tổng hợp điểm chất lượng)
**Tính điểm tổng thể:**
```python
quality_score = (
    row_count_score * 0.3 +
    freshness_score * 0.2 +
    null_score * 0.3 +
    duplicate_score * 0.2
)
```

**Đẩy vào XCom + ghi metrics Prometheus**

---

#### **6. alert_on_anomalies** (Cảnh báo khi phát hiện bất thường)
**Logic:**
```python
if quality_score < 90:
    return True  # Send alert
else:
    return False  # Skip alert
```

---

#### **7. send_alerts** (SlackOperator)
**Message:**
```
⚠️ Data Quality Alert - Score: 85/100

Issues Detected:
- fact_orders row count variance: 12%
- dim_customer null percentage: 8.5%

Action Required:
🔗 Investigate: http://localhost:8081/dags/sme_pulse_data_quality_monitor
```

---

## 📁 CẤU TRÚC CODE

```
airflow/
├── dags/
│   ├── sme_pulse_daily_etl.py              # DAG 1 - Main pipeline
│   ├── sme_pulse_external_data_sync.py     # DAG 2 - External data (existing)
│   ├── sme_pulse_data_quality_monitor.py   # DAG 3 - Monitoring
│   │
│   ├── config/
│   │   ├── pipeline_config.yml             # Global configs
│   │   ├── data_quality_thresholds.yml     # Alert thresholds
│   │   └── notification_config.yml         # Slack/Email configs
│   │
│   └── utils/
│       ├── __init__.py
│       ├── minio_helpers.py                # MinIO operations
│       ├── dbt_helpers.py                  # dbt command wrappers
│       ├── trino_helpers.py                # Trino query utilities
│       ├── notification_helpers.py         # Slack/Email helpers
│       └── data_quality_helpers.py         # DQ check functions
│
├── logs/                                   # Airflow logs
├── plugins/                                # Custom operators (if needed)
└── Dockerfile                              # Airflow container config
```

---

## ⚙️ CONFIGURATION FILES

### **pipeline_config.yml**
```yaml
minio:
  endpoint: localhost:9000
  access_key: minioadmin
  secret_key: minioadmin123
  bucket: sme-lake
  
trino:
  host: localhost
  port: 8080
  catalog: sme_lake
  schema: gold
  
dbt:
  profiles_dir: /opt/dbt
  project_dir: /opt/dbt
  target: dev
  
metabase:
  url: http://localhost:3000
  api_key: ${METABASE_API_KEY}
  database_id: 1
  
redis:
  host: localhost
  port: 6379
  db: 0
  
notifications:
  slack:
    webhook_url: ${SLACK_WEBHOOK_URL}
    channel: "#data-engineering"
  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    from_email: alerts@company.com
    to_emails: 
      - team@company.com
```

---

### **data_quality_thresholds.yml**
```yaml
row_count_variance:
  warning: 0.05   # 5%
  critical: 0.10  # 10%
  
data_freshness:
  warning_days: 1
  critical_days: 2
  
null_percentage:
  warning: 0.05   # 5%
  critical: 0.10  # 10%
  
duplicate_keys:
  warning: 0
  critical: 10
  
overall_quality_score:
  warning: 90
  critical: 80
```

---

## 🔄 EXECUTION FLOW - MAIN DAG

### **Timeline Example (Daily 2:00 AM run):**

```
02:00:00 - Pipeline Start
02:00:05 - verify_infrastructure [5s]
02:00:05 - bronze_ingestion start (parallel)
    02:00:10 - ingest_bank_transactions complete [25s]
    02:00:50 - ingest_shipments_payments complete [45s]
    02:01:30 - ingest_sales_snapshot complete [85s]
02:01:30 - bronze_validation [10s]
02:01:40 - dbt_seed_check_and_load [5s] (skipped - no changes)
02:01:40 - dbt_silver_staging [42s]
02:02:22 - dbt_silver_test [12s]
02:02:34 - dbt_gold_dims [15s] (parallel)
02:02:49 - dbt_gold_dims_test [5s]
02:02:54 - dbt_gold_facts [50s] (parallel)
02:03:44 - dbt_gold_facts_test [15s]
02:03:59 - dbt_gold_links [5s]
02:04:04 - dbt_gold_links_test [2s]
02:04:06 - serve_layer start (parallel)
    02:04:11 - metabase_refresh_cache [5s]
    02:04:07 - redis_invalidate_cache [1s]
02:04:11 - generate_pipeline_report [2s]
02:04:13 - notify_completion [1s]
02:04:14 - Pipeline End

Total Duration: ~4 minutes 14 seconds
```

---

## 📊 MONITORING & ALERTING

### **Metrics Tracked:**
1. **Pipeline Metrics:**
   - Execution duration
   - Task success/failure rates
   - Data volume processed
   - Retry counts

2. **Data Quality Metrics:**
   - Row counts per table
   - Null percentages
   - Duplicate key counts
   - Schema drift detection
   - Data freshness

3. **Infrastructure Metrics:**
   - MinIO storage usage
   - Trino query performance
   - Postgres connection pool
   - Redis cache hit rate

### **Alerting Channels:**
- **Slack:** Real-time notifications
- **Email:** Critical failures only
- **PagerDuty:** Production incidents (future)

### **Alert Severity Levels:**
- 🟢 **INFO:** Pipeline completed successfully
- 🟡 **WARNING:** Minor issues, auto-retried
- 🔴 **CRITICAL:** Pipeline failed, manual intervention needed

---

## 🔐 SECURITY & BEST PRACTICES

### **Secrets Management:**
```python
# Use Airflow Connections & Variables
minio_conn = Connection.get_connection_from_secrets('minio_default')
slack_webhook = Variable.get('slack_webhook_url')
metabase_key = Variable.get('metabase_api_key')
```

### **Idempotency:**
- All transformations use `CREATE OR REPLACE TABLE`
- Ingestion overwrites existing files (not append)
- Full refresh strategy (no incremental issues)

### **Error Handling:**
- Retries: 2 attempts with 5-minute delay
- Timeout: 30 minutes max per task
- On failure: Log context, don't block partial success

### **Performance Optimization:**
- Parallel execution where possible
- TaskGroups for logical grouping
- XCom size limits respected (<1MB per message)

---

## 🎯 SUCCESS CRITERIA

### **Pipeline Success Defined As:**
✅ All Bronze sources ingested successfully  
✅ Silver staging tables built with >95% row match  
✅ Gold dimensions & facts created without errors  
✅ Data quality tests pass >98%  
✅ Metabase cache refreshed  
✅ Total duration < 20 minutes  
✅ No critical alerts triggered  

### **Data Quality Score Formula:**
```
Score = (
    row_count_accuracy * 30% +
    schema_compliance * 20% +
    null_checks * 25% +
    referential_integrity * 15% +
    freshness * 10%
)

Acceptable Score: ≥ 95%
```

---

## 🚀 DEPLOYMENT CHECKLIST

### **Pre-Deployment:**
- [ ] All Python scripts tested in isolation
- [ ] dbt models compiled without errors
- [ ] MinIO buckets created and accessible
- [ ] Trino catalogs configured
- [ ] Airflow connections configured
- [ ] Secrets stored in Airflow Variables
- [ ] Slack/Email webhooks tested

### **Post-Deployment:**
- [ ] DAG appears in Airflow UI
- [ ] Manual trigger test successful
- [ ] All tasks green in first run
- [ ] Notifications received
- [ ] Metabase dashboards refreshed
- [ ] Monitor first 3 scheduled runs

---

## 📚 NEXT STEPS AFTER PHASE A

### **Phase B: ML Pipeline** (Future)
- Feature engineering DAG
- Model training DAG (Prophet, clustering)
- Model serving to Gold layer
- ML monitoring & drift detection

### **Phase C: Advanced Features** (Future)
- Incremental loading (SCD Type 2 for large tables)
- CDC (Change Data Capture) from source systems
- Real-time streaming ingestion (Kafka → Bronze)
- Multi-environment setup (dev/staging/prod)

---

## 📞 SUPPORT & CONTACTS

**Data Engineering Team:**
- Lead: [Your Name]
- Email: data-eng@company.com
- Slack: #data-engineering

**Airflow UI:** http://localhost:8081  
**Metabase:** http://localhost:3000  
**MinIO Console:** http://localhost:9001  
**Trino UI:** http://localhost:8080  

---

## 📝 DOCUMENT VERSION

- **Version:** 1.0
- **Last Updated:** 2025-11-03
- **Author:** AI Assistant + Data Engineering Team
- **Status:** APPROVED - Ready for Implementation

---

**🎉 END OF AIRFLOW ARCHITECTURE DOCUMENT**
