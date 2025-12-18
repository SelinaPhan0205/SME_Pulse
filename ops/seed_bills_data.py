"""
Script để thêm dữ liệu mẫu cho AP Bills (Công nợ phải trả)
Chạy: python ops/seed_bills_data.py
"""

import asyncio
import sys
from datetime import date, timedelta
from decimal import Decimal
import random

# Add backend path
sys.path.insert(0, 'backend')

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Database URL - sử dụng postgres_application_db (port 5433)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/sme_pulse_oltp"


async def seed_bills():
    """Thêm dữ liệu mẫu cho AP Bills"""
    
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # 1. Kiểm tra và lấy danh sách suppliers
            result = await session.execute(
                text("SELECT id, name, code FROM core.suppliers WHERE org_id = 1 LIMIT 10")
            )
            suppliers = result.fetchall()
            
            if not suppliers:
                print("❌ Không có supplier nào! Cần tạo supplier trước.")
                # Tạo suppliers mẫu
                print("📝 Đang tạo suppliers mẫu...")
                supplier_data = [
                    ("Công ty TNHH ABC", "SUP001", "abc@supplier.com", "0901234567"),
                    ("Công ty CP XYZ", "SUP002", "xyz@supplier.com", "0902345678"),
                    ("Nhà cung cấp Minh Phát", "SUP003", "minhphat@email.com", "0903456789"),
                    ("Công ty Vật tư Sài Gòn", "SUP004", "vattu@saigon.com", "0904567890"),
                    ("Đại lý Phương Nam", "SUP005", "phuongnam@email.com", "0905678901"),
                ]
                
                for name, code, email, phone in supplier_data:
                    # Check if supplier already exists
                    check_result = await session.execute(
                        text("SELECT id FROM core.suppliers WHERE org_id = 1 AND code = :code"),
                        {"code": code}
                    )
                    if check_result.fetchone() is None:
                        await session.execute(
                            text("""
                                INSERT INTO core.suppliers (name, code, email, phone, payment_term, is_active, org_id, created_at, updated_at)
                                VALUES (:name, :code, :email, :phone, 30, true, 1, NOW(), NOW())
                            """),
                            {"name": name, "code": code, "email": email, "phone": phone}
                        )
                await session.commit()
                
                # Lấy lại suppliers
                result = await session.execute(
                    text("SELECT id, name, code FROM core.suppliers WHERE org_id = 1 LIMIT 10")
                )
                suppliers = result.fetchall()
            
            print(f"✅ Tìm thấy {len(suppliers)} suppliers")
            for s in suppliers:
                print(f"   - ID {s[0]}: {s[1]} ({s[2]})")
            
            # 2. Tạo bills mẫu
            print("\n📝 Đang tạo bills mẫu...")
            
            today = date.today()
            bills_data = []
            
            # Tạo 10 bills với các status khác nhau
            statuses = ['unpaid', 'unpaid', 'unpaid', 'partial', 'partial', 'paid', 'paid', 'unpaid', 'unpaid', 'unpaid']
            
            for i in range(10):
                supplier = random.choice(suppliers)
                supplier_id = supplier[0]
                
                # Random dates
                issue_date = today - timedelta(days=random.randint(5, 30))
                due_date = issue_date + timedelta(days=random.randint(15, 45))
                
                # Random amounts
                total_amount = Decimal(random.randint(3, 50) * 1000000)  # 3M - 50M
                status = statuses[i]
                
                if status == 'paid':
                    paid_amount = total_amount
                elif status == 'partial':
                    paid_amount = Decimal(float(total_amount) * random.uniform(0.3, 0.7))
                else:
                    paid_amount = Decimal(0)
                
                bill_no = f"BILL-2025-{str(i+1).zfill(3)}"
                
                bills_data.append({
                    "bill_no": bill_no,
                    "supplier_id": supplier_id,
                    "issue_date": issue_date,
                    "due_date": due_date,
                    "total_amount": total_amount,
                    "paid_amount": paid_amount,
                    "status": status,
                    "notes": f"Hóa đơn mua hàng từ {supplier[1]}",
                    "org_id": 1,
                })
            
            # 3. Insert bills
            for bill in bills_data:
                await session.execute(
                    text("""
                        INSERT INTO finance.ap_bills 
                        (bill_no, supplier_id, issue_date, due_date, total_amount, paid_amount, status, notes, org_id, created_at, updated_at)
                        VALUES (:bill_no, :supplier_id, :issue_date, :due_date, :total_amount, :paid_amount, :status, :notes, :org_id, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    bill
                )
                print(f"   ✅ Tạo bill: {bill['bill_no']} - {bill['total_amount']:,.0f}đ - {bill['status']}")
            
            await session.commit()
            
            # 4. Verify
            result = await session.execute(
                text("SELECT COUNT(*) FROM finance.ap_bills WHERE org_id = 1")
            )
            count = result.scalar()
            print(f"\n✅ Hoàn thành! Tổng số bills: {count}")
            
            # Hiển thị thống kê
            result = await session.execute(
                text("""
                    SELECT status, COUNT(*), SUM(total_amount - paid_amount) as remaining
                    FROM finance.ap_bills 
                    WHERE org_id = 1
                    GROUP BY status
                """)
            )
            stats = result.fetchall()
            print("\n📊 Thống kê:")
            for stat in stats:
                print(f"   - {stat[0]}: {stat[1]} bills, còn phải trả: {stat[2]:,.0f}đ")
            
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_bills())
