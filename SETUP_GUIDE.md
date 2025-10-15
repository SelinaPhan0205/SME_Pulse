# 🚀 HƯỚNG DẪN SETUP SME PULSE - CHI TIẾT TỪNG BƯỚC

## 📋 Mục lục
1. [Kiểm tra điều kiện tiên quyết](#bước-1-kiểm-tra-điều-kiện-tiên-quyết)
2. [Copy file môi trường](#bước-2-copy-file-môi-trường)
3. [Khởi động Docker services](#bước-3-khởi-động-docker-services)
4. [Kiểm tra Postgres](#bước-4-kiểm-tra-postgres)
5. [Test dbt](#bước-5-test-dbt)
6. [Chạy dbt transform](#bước-6-chạy-dbt-transform)
7. [Kiểm tra kết quả](#bước-7-kiểm-tra-kết-quả)
8. [Truy cập Airflow](#bước-8-truy-cập-airflow)
9. [Setup Metabase](#bước-9-setup-metabase)
10. [Test Redis](#bước-10-test-redis)
11. [Troubleshooting](#troubleshooting)

---

## BƯỚC 1: Kiểm tra điều kiện tiên quyết

### 1.1. Kiểm tra Docker đã cài chưa
Mở PowerShell trong VS Code (Ctrl + `) và chạy:

```powershell
docker --version
docker compose version
```

**✅ Kết quả mong đợi:**
```
Docker version 24.0.x
Docker Compose version v2.x.x
```

❌ **Nếu lỗi**: Tải Docker Desktop tại https://www.docker.com/products/docker-desktop

### 1.2. Kiểm tra Docker đang chạy
```powershell
docker ps
```

**✅ Kết quả mong đợi:** Hiển thị danh sách containers (có thể rỗng)

❌ **Nếu lỗi "daemon not running"**: Mở Docker Desktop

---

## BƯỚC 2: Copy file môi trường

### 2.1. Copy .env.example thành .env
```powershell
Copy-Item .env.example .env
```

### 2.2. Xác nhận file đã được tạo
```powershell
Test-Path .env
```

**✅ Kết quả mong đợi:** `True`

### 2.3. (Tùy chọn) Đổi mật khẩu
Mở file `.env` trong VS Code và thay đổi:
- `POSTGRES_PASSWORD=supersecret` → mật khẩu mạnh hơn
- `MINIO_ROOT_PASSWORD=minio123` → mật khẩu mạnh hơn

---

## BƯỚC 3: Khởi động Docker services

### 3.1. Build và start tất cả services
```powershell
docker compose up -d
```

**Giải thích:**
- `up`: Khởi động services
- `-d`: Detached mode (chạy background)

**⏱️ Thời gian:** ~2-5 phút (lần đầu download images)

**✅ Kết quả mong đợi:**
```
[+] Running 5/5
 ✔ Container sme-postgres   Started
 ✔ Container sme-redis      Started
 ✔ Container sme-airflow    Started
 ✔ Container sme-metabase   Started
 ✔ Container sme-dbt        Created
```

### 3.2. Kiểm tra tất cả services đang chạy
```powershell
docker compose ps
```

**✅ Kết quả mong đợi:** Tất cả services có STATE = "running" hoặc "Up"

### 3.3. Xem logs real-time (nếu muốn debug)
```powershell
# Xem logs của tất cả services
docker compose logs -f

# Hoặc chỉ xem 1 service cụ thể
docker compose logs -f postgres
docker compose logs -f airflow
```

**Nhấn Ctrl+C để thoát khỏi logs**

---

## BƯỚC 4: Kiểm tra Postgres

### 4.1. Kiểm tra schemas đã được tạo
```powershell
docker compose exec postgres psql -U sme -d sme -c "\dn"
```

**Giải thích:**
- `exec postgres`: Chạy lệnh trong container postgres
- `psql -U sme -d sme`: Kết nối tới database 'sme' với user 'sme'
- `\dn`: Liệt kê tất cả schemas

**✅ Kết quả mong đợi:**
```
  Name   | Owner
---------+-------
 gold    | sme
 public  | sme
 raw     | sme
 silver  | sme
```

### 4.2. Kiểm tra dữ liệu mẫu đã được insert
```powershell
docker compose exec postgres psql -U sme -d sme -c "SELECT COUNT(*) FROM raw.transactions_raw;"
```

**✅ Kết quả mong đợi:**
```
 count
-------
     5
```

### 4.3. Xem chi tiết 5 đơn hàng mẫu
```powershell
docker compose exec postgres psql -U sme -d sme -c "SELECT event_id, payload_json->>'order_id' as order_id, (payload_json->>'total')::numeric as total FROM raw.transactions_raw;"
```

**✅ Kết quả mong đợi:** Hiển thị 5 orders với total từ 168,000 đến 472,500 VND

---

## BƯỚC 5: Test dbt

### 5.1. Test connection tới database
```powershell
docker compose run --rm dbt-runner dbt debug --profiles-dir /usr/app
```

**Giải thích:**
- `run --rm`: Chạy container tạm thời, tự động xóa sau khi xong
- `dbt debug`: Kiểm tra connection và config

**✅ Kết quả mong đợi:**
```
Connection test: [OK connection ok]
All checks passed!
```

❌ **Nếu lỗi "Could not connect"**: 
- Kiểm tra Postgres đã chạy: `docker compose ps postgres`
- Kiểm tra credentials trong `dbt/profiles.yml`

### 5.2. Install dbt packages (nếu cần)
```powershell
docker compose run --rm dbt-runner dbt deps --profiles-dir /usr/app
```

**✅ Kết quả:** `Installing dbt-labs/dbt_utils` (nếu có packages.yml)

---

## BƯỚC 6: Chạy dbt transform

### 6.1. Chạy Silver layer (staging)
```powershell
docker compose run --rm dbt-runner dbt run --select silver.stg_transactions --profiles-dir /usr/app
```

**⏱️ Thời gian:** ~5-10 giây

**✅ Kết quả mong đợi:**
```
Completed successfully
Done. PASS=1 WARN=0 ERROR=0 SKIP=0 TOTAL=1
```

**Giải thích:** dbt đã tạo bảng `silver.stg_transactions` từ `raw.transactions_raw`

### 6.2. Chạy Gold layer (aggregation)
```powershell
docker compose run --rm dbt-runner dbt run --select gold.fact_orders --profiles-dir /usr/app
```

**✅ Kết quả mong đợi:**
```
Completed successfully
Done. PASS=1 WARN=0 ERROR=0 SKIP=0 TOTAL=1
```

**Giải thích:** dbt đã tạo bảng `gold.fact_orders` tổng hợp doanh thu theo ngày

### 6.3. Chạy tất cả models cùng lúc
```powershell
docker compose run --rm dbt-runner dbt run --profiles-dir /usr/app
```

**✅ Kết quả:** PASS=2 (stg_transactions + fact_orders)

---

## BƯỚC 7: Kiểm tra kết quả

### 7.1. Kiểm tra Silver table
```powershell
docker compose exec postgres psql -U sme -d sme -c "SELECT COUNT(*) FROM silver.stg_transactions;"
```

**✅ Kết quả mong đợi:** `count = 5`

### 7.2. Kiểm tra Gold table - Doanh thu theo ngày
```powershell
docker compose exec postgres psql -U sme -d sme -c "SELECT order_date, total_orders, total_revenue FROM gold.fact_orders ORDER BY order_date;"
```

**✅ Kết quả mong đợi:**
```
 order_date | total_orders | total_revenue
------------+--------------+---------------
 2025-10-14 |            3 |        929250
 2025-10-15 |            2 |        509250
```

**Giải thích:**
- Ngày 14/10: 3 đơn hàng, tổng doanh thu 929,250 VND
- Ngày 15/10: 2 đơn hàng, tổng doanh thu 509,250 VND

---

## BƯỚC 8: Truy cập Airflow

### 8.1. Mở Airflow UI
Mở browser và truy cập: http://localhost:8080

**⏱️ Lưu ý:** Airflow cần ~30-60 giây để khởi động hoàn toàn

### 8.2. Login
- **Username:** `admin`
- **Password:** `admin`

### 8.3. Tìm DAG "sme_pulse_pipeline"
1. Trang chủ sẽ hiển thị danh sách DAGs
2. Tìm DAG có tên: `sme_pulse_pipeline`
3. Click vào toggle switch bên trái để **Unpause** DAG (chuyển thành xanh)

### 8.4. Chạy DAG thủ công (Manual Trigger)
1. Click vào tên DAG `sme_pulse_pipeline`
2. Click nút **Play** (▶️) ở góc phải trên
3. Chọn "Trigger DAG"

### 8.5. Xem kết quả
1. Click vào DAG run vừa tạo
2. Click vào tab **Graph** để xem flow
3. Click vào từng task để xem logs

**✅ Kết quả mong đợi:** Tất cả tasks màu xanh (success)

---

## BƯỚC 9: Setup Metabase

### 9.1. Mở Metabase
Mở browser: http://localhost:3000

**⏱️ Lần đầu:** Metabase cần ~30 giây để khởi động

### 9.2. Setup account (lần đầu tiên)
1. **Your name:** Admin User
2. **Email:** admin@sme-pulse.local
3. **Password:** [chọn mật khẩu mạnh]
4. Click "Next"

### 9.3. Connect tới Postgres
1. **Database type:** PostgreSQL
2. **Name:** SME Pulse
3. **Host:** `postgres` (tên service trong docker)
4. **Port:** `5432`
5. **Database name:** `sme`
6. **Username:** `sme`
7. **Password:** `supersecret` (hoặc password bạn đã đổi trong .env)
8. Click "Connect database"

### 9.4. Tạo dashboard đơn giản
1. Click "New" → "Question"
2. Chọn database "SME Pulse"
3. Chọn schema "gold"
4. Chọn table "fact_orders"
5. **Visualization:** Line chart
   - X-axis: `order_date`
   - Y-axis: `total_revenue`
6. Click "Visualize"
7. Click "Save" → đặt tên "Daily Revenue"

**✅ Kết quả:** Chart hiển thị doanh thu 2 ngày (14/10 và 15/10)

---

## BƯỚC 10: Test Redis

### 10.1. Kiểm tra Redis đang chạy
```powershell
docker compose exec redis redis-cli ping
```

**✅ Kết quả mong đợi:** `PONG`

### 10.2. Set/Get key thử nghiệm
```powershell
# Set key
docker compose exec redis redis-cli SET test:key "Hello SME Pulse"

# Get key
docker compose exec redis redis-cli GET test:key
```

**✅ Kết quả:** `"Hello SME Pulse"`

### 10.3. Test invalidate script
```powershell
# Set một số keys test
docker compose exec redis redis-cli SET "v1:org-sme-001:cash:overview" '{"balance": 1000000}'
docker compose exec redis redis-cli SET "v1:org-sme-001:revenue:daily" '{"revenue": 500000}'

# Kiểm tra keys đã tồn tại
docker compose exec redis redis-cli KEYS "v1:*"

# Chạy invalidate script (cần cài redis-py trong container)
# Placeholder - trong production sẽ chạy từ Airflow
```

---

## BƯỚC 11: (Optional) Enable MinIO

### 11.1. Uncomment MinIO trong docker-compose.yml
Mở file `docker-compose.yml`, tìm đến phần MinIO và bỏ comment:

```yaml
# Trước:
  # minio:
  #   image: minio/minio:latest
  #   ...

# Sau:
  minio:
    image: minio/minio:latest
    ...
```

### 11.2. Restart services
```powershell
docker compose up -d
```

### 11.3. Truy cập MinIO Console
Mở browser: http://localhost:9001

- **Username:** `minio` (từ .env)
- **Password:** `minio123` (từ .env)

### 11.4. Tạo bucket
1. Click "Buckets" → "Create Bucket"
2. **Bucket Name:** `sme-pulse`
3. Click "Create Bucket"

---

## 🎉 HOÀN THÀNH!

Bạn đã setup thành công SME Pulse data platform! 

**Kiểm tra lại toàn bộ:**
```powershell
# 1. All services running
docker compose ps

# 2. Data có trong Gold table
docker compose exec postgres psql -U sme -d sme -c "SELECT * FROM gold.fact_orders;"

# 3. Airflow accessible
# Mở: http://localhost:8080

# 4. Metabase accessible
# Mở: http://localhost:3000
```

---

## 🔧 TROUBLESHOOTING

### Lỗi: "Port already in use"
```powershell
# Tìm process đang dùng port
netstat -ano | findstr :8080
netstat -ano | findstr :5432

# Giải pháp 1: Kill process
Stop-Process -Id [PID] -Force

# Giải pháp 2: Đổi port trong .env
# Ví dụ: POSTGRES_PORT=5433
```

### Lỗi: "Permission denied" (Airflow logs)
```powershell
# Tạo lại thư mục với quyền đầy đủ
Remove-Item -Recurse -Force airflow/logs
New-Item -ItemType Directory -Path airflow/logs

# Restart services
docker compose restart airflow
```

### Lỗi: dbt "Compilation Error"
```powershell
# Xem logs chi tiết
docker compose run --rm dbt-runner dbt run --select stg_transactions --profiles-dir /usr/app --debug

# Thường do:
# 1. Syntax error trong SQL
# 2. Table không tồn tại trong raw schema
```

### Reset toàn bộ project
```powershell
# Dừng và xóa tất cả
docker compose down -v

# Xóa logs
Remove-Item -Recurse -Force airflow/logs/*

# Start lại
docker compose up -d
```

### Xem logs của service cụ thể
```powershell
docker compose logs -f [service-name]

# Ví dụ:
docker compose logs -f postgres
docker compose logs -f airflow
docker compose logs -f dbt-runner
```

---

## 📚 NEXT STEPS

### 1. Thêm Airbyte để tự động ingest
Xem file `AIRBYTE_SETUP.md` (sẽ tạo riêng)

### 2. Thêm Great Expectations cho DQ
```powershell
# Tạo GX config
docker compose run --rm dbt-runner pip install great-expectations
```

### 3. Thêm monitoring với Prometheus/Grafana
Xem file `MONITORING_SETUP.md`

### 4. Deploy lên production
- Đổi passwords trong .env
- Setup backup cho Postgres
- Setup SSL cho các endpoints

---

**📞 Support:**
- GitHub Issues: [link]
- Slack: #sme-pulse-support
- Email: support@sme-pulse.local
