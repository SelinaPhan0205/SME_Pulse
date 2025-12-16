# SME Pulse - Tổng Kết Kinh Nghiệm & Lỗi Thường Gặp

## 1. Tổng quan kiến trúc thực tế
- Medallion Lakehouse: 1 catalog duy nhất (`sme_lake`) với 3 schema: bronze, silver, gold.
- Trino + Iceberg + MinIO (S3) + Hive Metastore: Truy vấn, lưu trữ, quản lý metadata tập trung.
- dbt: Chuyển đổi dữ liệu, tổ chức theo chuẩn Medallion.
- Airflow: Orchestration, trigger pipeline, kiểm soát lỗi.
- Tất cả service chạy qua Docker Compose, dùng volume và .env đồng bộ.

## 2. Lỗi thường gặp & cách xử lý triệt để

### a. Airflow DAG stuck ở trạng thái "queued"
- **Nguyên nhân:** Scheduler không chạy hoặc không healthy.
- **Giải pháp:**
  - Chạy scheduler và webserver ở 2 container riêng biệt.
  - Đảm bảo healthcheck, restart policy đúng.

### b. Lỗi kết nối MinIO (Connection refused/localhost:9000)
- **Nguyên nhân:** Dùng endpoint `localhost:9000` thay vì `minio:9000` trong Docker.
- **Giải pháp:** Luôn dùng tên service Docker (`minio:9000`) trong config/code.

### c. Lỗi permission denied khi chạy dbt (target/partial_parse.msgpack)
- **Nguyên nhân:** Quyền thư mục/volume `dbt/target` không đúng (do mount từ host Windows hoặc user khác tạo ra).
- **Giải pháp:**
  - Xóa sạch thư mục `dbt/target` trên host, để dbt tự tạo lại.
  - Nếu vẫn lỗi, mount volume Docker riêng cho `/opt/dbt/target`.

### d. Lỗi thiếu package Python (openpyxl...)
- **Nguyên nhân:** Chưa cài package vào Dockerfile Airflow.
- **Giải pháp:** Thêm vào lệnh `pip install` trong Dockerfile, build lại image.

### e. Lỗi khi gọi hàm ingest trong Airflow (unexpected keyword argument)
- **Nguyên nhân:** Hàm main() không nhận đúng tham số.
- **Giải pháp:** Refactor hàm main() nhận đúng `folder`, `prefix`, `combine`...

### f. Lỗi docker exec trong Airflow (dbt deps)
- **Nguyên nhân:** Không nên orchestration dbt deps qua docker exec trong Airflow.
- **Giải pháp:** Chạy `dbt deps` khi build image dbt hoặc khi container dbt khởi động.

## 3. Kinh nghiệm thực chiến
- Luôn dùng tên service Docker khi cấu hình endpoint giữa các container.
- Tách rõ các volume mount từ host và volume Docker để tránh lỗi quyền trên Windows.
- Đảm bảo các script Python nhận tham số linh hoạt (qua cả CLI và kwargs).
- Khi gặp lỗi permission, xóa cache/target và để service tự tạo lại.
- Đọc kỹ log Airflow, log container để xác định đúng nguyên nhân lỗi.
- Đảm bảo healthcheck cho mọi service trong docker-compose để pipeline tự động recover.

## 4. Lỗi thực tế khác & bài học quyền truy cập

### g. Lỗi quyền truy cập S3A/Iceberg/MinIO (Access Denied, PermissionError)
- **Nguyên nhân:**
  - Cấu hình sai access key/secret key cho MinIO trong Trino, Hive Metastore, hoặc dbt.
  - User airflow hoặc các service khác không có quyền truy cập bucket hoặc prefix trên MinIO.
  - Thiếu cấu hình `s3.path-style-access=true` hoặc endpoint không đúng.
- **Giải pháp:**
  - Đảm bảo mọi service (Trino, Hive Metastore, dbt, Airflow) đều dùng đúng access key/secret key và endpoint MinIO.
  - Luôn cấu hình `s3.path-style-access=true` trong Trino và các client.
  - Kiểm tra quyền bucket trên MinIO, tạo bucket trước khi ghi nếu cần.
  - Nếu dùng nhiều user, đảm bảo user airflow có quyền ghi/đọc trên bucket MinIO.

### h. Lỗi quyền user airflow khi mount volume hoặc chạy script
- **Nguyên nhân:**
  - File/folder được tạo bởi user khác (root, user host) nên airflow không ghi/xóa được.
  - Mount volume từ host Windows gây lỗi quyền ảo.
- **Giải pháp:**
  - Luôn mount volume với quyền phù hợp, ưu tiên volume Docker thay vì bind-mount từ host nếu gặp lỗi quyền.
  - Nếu cần, thêm lệnh `chown` hoặc xóa sạch folder để airflow tự tạo lại.
  - Đảm bảo Dockerfile và entrypoint không chạy lệnh với user root nếu không cần thiết.

### i. Lỗi cấu hình S3A trong Hive Metastore hoặc Trino
- **Nguyên nhân:**
  - Thiếu hoặc sai các tham số như `fs.s3a.endpoint`, `fs.s3a.access.key`, `fs.s3a.secret.key` trong core-site.xml hoặc properties.
- **Giải pháp:**
  - Đảm bảo các file cấu hình đều đồng bộ endpoint, access key, secret key, region, path style.
  - Kiểm tra log Hive Metastore, Trino để phát hiện lỗi permission hoặc endpoint.

---
**Tài liệu này sẽ giúp bạn tiết kiệm hàng giờ debug khi triển khai Lakehouse stack thực tế!**
