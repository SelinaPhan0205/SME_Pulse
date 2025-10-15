# SME Pulse - ELT Data Platform

🎯 **Mục đích**: Xây dựng data pipeline cho doanh nghiệp vừa và nhỏ (SME)

## 📋 Kiến trúc hệ thống

```
Nguồn dữ liệu → Postgres (Raw) → dbt Transform → Postgres (Silver/Gold) → Dashboard
                                      ↓
                                  Redis Cache
```

## 🛠️ Stack công nghệ

- **Postgres 15**: Kho dữ liệu chính
- **Redis 7**: Cache layer
- **Airflow 2**: Điều phối pipeline
- **dbt**: Transform dữ liệu
- **Metabase**: BI dashboard
- **MinIO** (optional): Data lake

## 🚀 Hướng dẫn khởi động

### 1. Copy file môi trường
```powershell
Copy-Item .env.example .env
```

### 2. Chỉnh sửa mật khẩu (tùy chọn)
Mở file `.env` và thay đổi các giá trị `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD` nếu muốn.

### 3. Khởi động toàn bộ services
```powershell
docker compose up -d
```

### 4. Kiểm tra services đang chạy
```powershell
docker compose ps
```

### 5. Truy cập các UI

- **Airflow**: http://localhost:8080 (admin/admin)
- **Metabase**: http://localhost:3000
- **MinIO Console**: http://localhost:9001 (minio/minio123)

## 📁 Cấu trúc dự án

```
sme-pulse/
├── docker-compose.yml      # Định nghĩa các services
├── .env                    # Biến môi trường
├── sql/init.sql           # Script khởi tạo database
├── airflow/
│   └── dags/
│       └── sme_pulse.py   # DAG chính
├── dbt/
│   ├── dbt_project.yml    # Config dbt
│   ├── profiles.yml       # Connection config
│   └── models/
│       ├── silver/        # Staging models
│       └── gold/          # Aggregated models
├── ops/
│   └── invalidate.py      # Script invalidate cache
└── README.md
```

## 🧪 Smoke Test

Sau khi setup xong, chạy các lệnh sau để test:

```powershell
# 1. Kiểm tra Postgres
docker compose exec postgres psql -U sme -d sme -c "\dn"

# 2. Test dbt
docker compose run --rm dbt-runner dbt debug

# 3. Chạy transform
docker compose run --rm dbt-runner dbt run

# 4. Kiểm tra dữ liệu
docker compose exec postgres psql -U sme -d sme -c "SELECT * FROM gold.fact_orders LIMIT 5;"
```

## 📊 Data Flow

1. **Ingest**: Dữ liệu thô vào `raw` schema
2. **Clean**: dbt transform → `silver` schema (staging)
3. **Aggregate**: dbt transform → `gold` schema (fact tables)
4. **Cache**: Redis cache kết quả query
5. **Visualize**: Metabase đọc từ `gold` schema

## 🔧 Troubleshooting

### Lỗi permission denied
```powershell
docker compose down -v
docker compose up -d
```

### Xem logs của service
```powershell
docker compose logs -f [service-name]
# Ví dụ: docker compose logs -f airflow
```

### Reset toàn bộ
```powershell
docker compose down -v
Remove-Item -Recurse -Force airflow/logs/*
docker compose up -d
```

## 📚 Tài liệu tham khảo

- [dbt Documentation](https://docs.getdbt.com/)
- [Airflow Documentation](https://airflow.apache.org/docs/)
- [Metabase Documentation](https://www.metabase.com/docs/)

---

**Tác giả**: SME Pulse Team  
**Ngày tạo**: October 2025
