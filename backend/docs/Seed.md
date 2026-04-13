# 🌱 Seed Data Guide - SME Pulse Backend

## Mục đích
Seed data được dùng để **populate dữ liệu mẫu** vào database cho môi trường **development** và **testing**. Không dùng cho production.

---

## 📁 Cấu trúc thư mục Seed

```
backend/app/db/seeds/
├── __init__.py                          # Package marker
├── seed_roles.py                        # Seed các role hệ thống
├── seed_organizations.py                # Seed organization mặc định
├── seed_users.py                        # Seed admin user
├── seed_customers_suppliers.py          # Seed khách hàng và nhà cung cấp
├── seed_accounts.py                     # Seed các tài khoản (cash/bank)
└── run_all.py                           # Master orchestrator chạy tất cả seeds
```

---

## 🔑 Các File Seed Chi Tiết

### 1️⃣ seed_roles.py
**Mục đích:** Tạo các role trong hệ thống

**Data được tạo:**
```
- owner (Owner)
- accountant (Accountant)
- cashier (Cashier)
- admin (System Administrator)
```

**Cách chạy riêng:**
```bash
docker exec -it sme-backend python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.seeds.seed_roles import seed_roles

async def run():
    async with AsyncSessionLocal() as session:
        await seed_roles(session)
        await session.commit()

asyncio.run(run())
"
```

---

### 2️⃣ seed_organizations.py
**Mục đích:** Tạo organization mặc định (tenant gốc)

**Data được tạo:**
```
Tên: SME Demo Company
Tax Code: 1234567890
Địa chỉ: Ho Chi Minh City, Vietnam
```

**Lưu ý:** 
- Tất cả user, customer, supplier, account đều liên kết với organization này
- Organization là tenant root cho multi-tenancy

**Cách chạy riêng:**
```bash
docker exec -it sme-backend python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.seeds.seed_organizations import seed_organizations

async def run():
    async with AsyncSessionLocal() as session:
        await seed_organizations(session)
        await session.commit()

asyncio.run(run())
"
```

---

### 3️⃣ seed_users.py
**Mục đích:** Tạo admin user với 2 role (Owner + Administrator)

**Data được tạo:**
```
Email: admin@sme.com
Password: 123456 (được hash bằng bcrypt)
Full Name: Administrator
Status: active
Roles: Owner, System Administrator
```

**Cách chạy riêng:**
```bash
docker exec -it sme-backend python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.seeds.seed_users import seed_users

async def run():
    async with AsyncSessionLocal() as session:
        await seed_users(session)
        await session.commit()

asyncio.run(run())
"
```

---

### 4️⃣ seed_customers_suppliers.py
**Mục đực:** Tạo khách hàng và nhà cung cấp mẫu

**Customers được tạo:**
```
1. Code: CUS001
   Name: Alpha Trading
   Tax Code: 1111111111
   Credit Term: 30 days

2. Code: CUS002
   Name: Beta Retail
   Tax Code: 2222222222
   Credit Term: 45 days
```

**Suppliers được tạo:**
```
1. Code: SUP001
   Name: Thanh Son Logistics
   Tax Code: 3333333333
   Payment Term: 30 days

2. Code: SUP002
   Name: UIT Tech Vendor
   Tax Code: 4444444444
   Payment Term: 15 days
```

**Cách chạy riêng:**
```bash
docker exec -it sme-backend python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.seeds.seed_customers_suppliers import seed_customers_suppliers

async def run():
    async with AsyncSessionLocal() as session:
        await seed_customers_suppliers(session)
        await session.commit()

asyncio.run(run())
"
```

---

### 5️⃣ seed_accounts.py
**Mục đích:** Tạo tài khoản thanh toán (cash / bank)

**Accounts được tạo:**
```
1. Name: Cash Drawer
   Type: cash

2. Name: VCB Main Bank
   Type: bank
   Account Number: 0123456789
   Bank Name: Vietcombank
```

**Cách chạy riêng:**
```bash
docker exec -it sme-backend python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.seeds.seed_accounts import seed_accounts

async def run():
    async with AsyncSessionLocal() as session:
        await seed_accounts(session)
        await session.commit()

asyncio.run(run())
"
```

---

### 6️⃣ run_all.py
**Mục đích:** Master script chạy tất cả seeds theo đúng thứ tự

**Thứ tự chạy:**
```
1. seed_roles()                  → Tạo 4 roles
2. seed_organizations()         → Tạo 1 organization
3. seed_users()                 → Tạo admin user + gán roles
4. seed_customers_suppliers()   → Tạo 2 customers + 2 suppliers
5. seed_accounts()              → Tạo 2 accounts
```

**Output khi chạy thành công:**
```
🌱 Starting database seed...

[seed] Inserted role: owner
[seed] Inserted role: accountant
[seed] Inserted role: cashier
[seed] Inserted role: admin
[seed] Created default organization
[seed] Created admin user (email: admin@sme.com, password: 123456)
[seed] Assigned role Owner to admin user
[seed] Assigned role Admin to admin user
[seed] Inserted customer CUS001
[seed] Inserted customer CUS002
[seed] Inserted supplier SUP001
[seed] Inserted supplier SUP002
[seed] Inserted account Cash Drawer
[seed] Inserted account VCB Main Bank

============================================================
🎉 SEED COMPLETED SUCCESSFULLY!
============================================================

✅ Test Login Credentials:
   Email: admin@sme.com
   Password: 123456
   Roles: Owner, System Administrator
```

---

## 🚀 Cách Sử Dụng

### Chạy tất cả seeds cùng lúc
```bash
docker exec -it sme-backend python app/db/seeds/run_all.py
```

### Chạy seed riêng lẻ
Xem phần chi tiết của từng file ở trên.

### Reset database

#### 🟡 Cách 1 — Xóa dữ liệu (Nhanh, giữ schema)

```bash
docker exec -it sme-postgres-app psql -U postgres -d sme_pulse_oltp -c "
DELETE FROM core.user_roles;
DELETE FROM core.users;
DELETE FROM core.accounts;
DELETE FROM core.customers;
DELETE FROM core.suppliers;
DELETE FROM core.roles;
DELETE FROM core.organizations;
"
```

✔️ **Ưu điểm**
- Nhanh, giữ lại schema của database
- Chỉ xóa dữ liệu seed

❌ **Nhược điểm**
- Không clean migration history
- Nếu có lỗi schema vẫn tồn tại

Sau đó chạy lại seed:
```bash
docker exec -it sme-backend python app/db/seeds/run_all.py
```

---

#### 🟢 Cách 2 — Xóa toàn DB (Phổ biến nhất trong DEV)

```bash
docker volume rm sme_pulse_postgres-app-data
docker compose up -d --build
docker exec -it sme-backend python app/db/seeds/run_all.py
```

✔️ **Ưu điểm**
- Fresh 100%
- Mọi migrations chạy từ đầu
- Luôn đảm bảo DB nhất quán

❌ **Nhược điểm**
- Mất sạch tất cả dữ liệu
- Tốn thời gian chạy lại migrations

---

**Khuyến cáo:** Dùng **Cách 2** nếu muốn **clean state**, dùng **Cách 1** nếu chỉ muốn **quick reset**

---


## 🔐 Verify Dữ Liệu Được Tạo

### Check Roles
```bash
docker exec -it sme-postgres-app psql -U postgres -d sme_pulse_oltp -c "
SELECT id, code, name FROM core.roles ORDER BY id;
"
```

### Check Organization
```bash
docker exec -it sme-postgres-app psql -U postgres -d sme_pulse_oltp -c "
SELECT id, name, tax_code FROM core.organizations;
"
```

### Check Admin User
```bash
docker exec -it sme-postgres-app psql -U postgres -d sme_pulse_oltp -c "
SELECT id, email, full_name, status FROM core.users;
"
```

### Check User Roles
```bash
docker exec -it sme-postgres-app psql -U postgres -d sme_pulse_oltp -c "
SELECT u.email, r.code FROM core.users u 
JOIN core.user_roles ur ON u.id = ur.user_id 
JOIN core.roles r ON ur.role_id = r.id 
ORDER BY u.id;
"
```

### Check Customers
```bash
docker exec -it sme-postgres-app psql -U postgres -d sme_pulse_oltp -c "
SELECT id, code, name, tax_code, credit_term FROM core.customers;
"
```

### Check Suppliers
```bash
docker exec -it sme-postgres-app psql -U postgres -d sme_pulse_oltp -c "
SELECT id, code, name, tax_code, payment_term FROM core.suppliers;
"
```

### Check Accounts
```bash
docker exec -it sme-postgres-app psql -U postgres -d sme_pulse_oltp -c "
SELECT id, name, type, account_number, bank_name FROM core.accounts;
"
```

---

## 🎁 Tính Năng Seed

✅ **Idempotent:** Chạy nhiều lần không bị lỗi, nếu data đã tồn tại sẽ bỏ qua
✅ **Ordered:** Đảm bảo thứ tự chạy (roles → org → users → customers/suppliers → accounts)
✅ **Transaction:** Tất cả thay đổi được commit cùng lúc, nếu lỗi sẽ rollback
✅ **Verbose:** In log chi tiết từng bước

---

## 📝 Ghi chú khi muốn mở rộng Seed

Nếu muốn thêm seed khác (invoices, payments, alerts...), tạo file mới:

```python
# backend/app/db/seeds/seed_invoices.py
from sqlalchemy import select
from app.models.finance import Invoice
from app.models.core import Organization, Customer

async def seed_invoices(session):
    """Insert sample invoices."""
    org = (await session.execute(select(Organization))).scalar_one()
    customer = (await session.execute(select(Customer).where(Customer.code == "CUS001"))).scalar_one()
    
    invoices = [
        {
            "invoice_number": "INV001",
            "customer_id": customer.id,
            "org_id": org.id,
            "amount": 10000000,  # 10 triệu
        },
    ]
    
    for inv in invoices:
        exists = await session.execute(select(Invoice).where(Invoice.invoice_number == inv["invoice_number"]))
        if not exists.scalar_one_or_none():
            session.add(Invoice(**inv))
            print(f"[seed] Inserted invoice {inv['invoice_number']}")
```

Sau đó thêm vào `run_all.py`:
```python
from app.db.seeds.seed_invoices import seed_invoices

async def run_all_seeds():
    async with AsyncSessionLocal() as session:
        # ... existing seeds ...
        await seed_invoices(session)
        await session.commit()
```

---

## 🎯 Kết luận

Seed data là công cụ hữu ích để:
- ✅ Giúp developer test API mà không cần tạo data thủ công
- ✅ Chuẩn bị environment cho testing
- ✅ Demo application cho team
- ✅ Kiểm tra business logic

**QUAN TRỌNG:** Seed chỉ dùng cho **development**, không dùng cho **production**!
