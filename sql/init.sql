-- ===================================================
-- SME Pulse - Database Initialization Script
-- ===================================================
-- Mục đích: Tạo schemas và user cho data pipeline
-- Thực thi: Tự động khi Postgres container khởi động lần đầu
-- ===================================================

\echo '🚀 Bắt đầu khởi tạo database cho SME Pulse...'

-- ===== TẠO DATABASE CHO HIVE METASTORE =====
\echo '🗄️ Tạo database cho Hive Metastore...'

-- Tạo database riêng cho Hive Metastore (nếu chưa có)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'metastore_db') THEN
        PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE metastore_db');
    END IF;
END
$$;

\echo '✅ Database metastore_db đã sẵn sàng!'

-- ===== TẠO CÁC SCHEMAS =====
\echo '📁 Tạo schemas: raw, silver, gold...'

-- Schema RAW: Lưu dữ liệu thô từ các nguồn (POS, Payments, Shipments, Bank)
CREATE SCHEMA IF NOT EXISTS raw;
COMMENT ON SCHEMA raw IS 'Dữ liệu thô chưa được xử lý (Bronze layer)';

-- Schema SILVER: Dữ liệu đã được làm sạch và chuẩn hóa
CREATE SCHEMA IF NOT EXISTS silver;
COMMENT ON SCHEMA silver IS 'Dữ liệu đã làm sạch và chuẩn hóa (Silver layer)';

-- Schema GOLD: Dữ liệu đã được tổng hợp, sẵn sàng cho báo cáo
CREATE SCHEMA IF NOT EXISTS gold;
COMMENT ON SCHEMA gold IS 'Dữ liệu tổng hợp cho analytics (Gold layer)';

\echo '✅ Tạo schemas thành công!'

-- ===== TẠO APPLICATION USER =====
\echo '👤 Tạo user: app_user...'

-- Tạo role app_user với mật khẩu
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
    CREATE ROLE app_user WITH LOGIN PASSWORD 'app_pass';
    RAISE NOTICE 'User app_user đã được tạo';
  ELSE
    RAISE NOTICE 'User app_user đã tồn tại';
  END IF;
END
$$;

\echo '✅ User app_user đã sẵn sàng!'

-- ===== CẤP QUYỀN CHO USER =====
\echo '🔐 Cấp quyền cho app_user...'

-- Cấp quyền sử dụng schemas
GRANT USAGE ON SCHEMA raw TO app_user;
GRANT USAGE ON SCHEMA silver TO app_user;
GRANT USAGE ON SCHEMA gold TO app_user;

-- Cấp quyền đầy đủ cho schema raw (để insert dữ liệu thô)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA raw TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT ALL PRIVILEGES ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT ALL PRIVILEGES ON SEQUENCES TO app_user;

-- Cấp quyền đầy đủ cho schema silver (để dbt transform)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA silver TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA silver TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT ALL PRIVILEGES ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT ALL PRIVILEGES ON SEQUENCES TO app_user;

-- Cấp quyền đầy đủ cho schema gold (để dbt aggregate)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gold TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gold TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT ALL PRIVILEGES ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT ALL PRIVILEGES ON SEQUENCES TO app_user;

\echo '✅ Cấp quyền thành công!'

-- ===== TẠO BẢNG RAW.TRANSACTIONS_RAW =====
\echo '📊 Tạo bảng raw.transactions_raw...'

CREATE TABLE IF NOT EXISTS raw.transactions_raw (
    id SERIAL PRIMARY KEY,
    payload_json JSONB NOT NULL,        -- Dữ liệu JSON gốc từ nguồn
    source TEXT NOT NULL,               -- Nguồn dữ liệu: 'pos', 'payment', 'shipment', 'bank'
    domain TEXT NOT NULL,               -- Loại nghiệp vụ: 'order', 'payment', 'delivery', etc.
    event_id TEXT NOT NULL UNIQUE,      -- ID duy nhất của event
    updated_at TIMESTAMPTZ NOT NULL,    -- Thời gian cập nhật (dùng cho incremental load)
    ingested_at TIMESTAMPTZ DEFAULT NOW(), -- Thời gian nhập vào hệ thống
    hash TEXT NOT NULL,                 -- Hash để đảm bảo idempotent
    org_id TEXT NOT NULL,               -- Organization ID (multi-tenant)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index để tăng tốc query
CREATE INDEX IF NOT EXISTS idx_transactions_raw_event_id ON raw.transactions_raw(event_id);
CREATE INDEX IF NOT EXISTS idx_transactions_raw_updated_at ON raw.transactions_raw(updated_at);
CREATE INDEX IF NOT EXISTS idx_transactions_raw_domain ON raw.transactions_raw(domain);
CREATE INDEX IF NOT EXISTS idx_transactions_raw_org_id ON raw.transactions_raw(org_id);
CREATE INDEX IF NOT EXISTS idx_transactions_raw_source ON raw.transactions_raw(source);

COMMENT ON TABLE raw.transactions_raw IS 'Bảng lưu tất cả transactions từ các nguồn';
COMMENT ON COLUMN raw.transactions_raw.payload_json IS 'Dữ liệu JSON gốc từ API/CSV';
COMMENT ON COLUMN raw.transactions_raw.event_id IS 'ID duy nhất để tránh duplicate';
COMMENT ON COLUMN raw.transactions_raw.hash IS 'MD5 hash của payload để kiểm tra thay đổi';

\echo '✅ Bảng raw.transactions_raw đã sẵn sàng!'

-- ===== TẠO SAMPLE DATA =====
\echo '🌱 Tạo dữ liệu mẫu (sample data)...'

-- Xóa dữ liệu cũ nếu có (để script idempotent)
TRUNCATE TABLE raw.transactions_raw RESTART IDENTITY CASCADE;

-- Insert 5 sample orders
INSERT INTO raw.transactions_raw (payload_json, source, domain, event_id, updated_at, hash, org_id)
VALUES
  (
    '{"order_id": "ORD-2025-001", "order_ts": "2025-10-14T10:30:00Z", "subtotal": 150000, "discount": 10000, "shipping_fee": 20000, "tax": 8000, "total": 168000, "currency": "VND", "customer_id": "CUST-001", "payment_method": "credit_card", "status": "completed"}'::jsonb,
    'pos',
    'order',
    'evt-order-001',
    '2025-10-14 10:30:00+07',
    'hash001',
    'org-sme-001'
  ),
  (
    '{"order_id": "ORD-2025-002", "order_ts": "2025-10-14T11:15:00Z", "subtotal": 250000, "discount": 0, "shipping_fee": 25000, "tax": 13750, "total": 288750, "currency": "VND", "customer_id": "CUST-002", "payment_method": "cash", "status": "completed"}'::jsonb,
    'pos',
    'order',
    'evt-order-002',
    '2025-10-14 11:15:00+07',
    'hash002',
    'org-sme-001'
  ),
  (
    '{"order_id": "ORD-2025-003", "order_ts": "2025-10-14T14:20:00Z", "subtotal": 500000, "discount": 50000, "shipping_fee": 0, "tax": 22500, "total": 472500, "currency": "VND", "customer_id": "CUST-003", "payment_method": "bank_transfer", "status": "completed"}'::jsonb,
    'pos',
    'order',
    'evt-order-003',
    '2025-10-14 14:20:00+07',
    'hash003',
    'org-sme-001'
  ),
  (
    '{"order_id": "ORD-2025-004", "order_ts": "2025-10-15T09:45:00Z", "subtotal": 180000, "discount": 20000, "shipping_fee": 15000, "tax": 8750, "total": 183750, "currency": "VND", "customer_id": "CUST-004", "payment_method": "e_wallet", "status": "completed"}'::jsonb,
    'pos',
    'order',
    'evt-order-004',
    '2025-10-15 09:45:00+07',
    'hash004',
    'org-sme-001'
  ),
  (
    '{"order_id": "ORD-2025-005", "order_ts": "2025-10-15T13:00:00Z", "subtotal": 320000, "discount": 30000, "shipping_fee": 20000, "tax": 15500, "total": 325500, "currency": "VND", "customer_id": "CUST-005", "payment_method": "credit_card", "status": "completed"}'::jsonb,
    'pos',
    'order',
    'evt-order-005',
    '2025-10-15 13:00:00+07',
    'hash005',
    'org-sme-001'
  );

\echo '✅ Đã tạo 5 đơn hàng mẫu!'

-- ===== KIỂM TRA KẾT QUẢ =====
\echo '🔍 Kiểm tra dữ liệu vừa tạo...'
SELECT 
    id, 
    source, 
    domain, 
    event_id, 
    payload_json->>'order_id' as order_id,
    (payload_json->>'total')::numeric as total,
    org_id,
    updated_at
FROM raw.transactions_raw
ORDER BY updated_at;

\echo ''
\echo '✨ Khởi tạo database hoàn tất!'
\echo '📊 Có thể kiểm tra bằng lệnh: docker compose exec postgres psql -U sme -d sme -c "SELECT COUNT(*) FROM raw.transactions_raw;"'
