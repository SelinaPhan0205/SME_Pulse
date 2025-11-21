# SME Pulse Backend - Setup & Migration Guide

## 📋 Tổng Quan Dự Án

**Date:** November 19, 2025  
**Version:** 1.0.0  
**Architecture:** Modular Monolith with Domain-Driven Design  
**Stack:** FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL + Alembic

---

## 🏗️ Backend Architecture

### Technology Stack
```
┌─────────────────────────────────────────┐
│         FastAPI 0.115.0                 │  ← REST API Framework
├─────────────────────────────────────────┤
│    SQLAlchemy 2.0.36 (Async ORM)       │  ← Data Access Layer
├─────────────────────────────────────────┤
│    Alembic 1.14.0 (Migrations)         │  ← Schema Versioning
├─────────────────────────────────────────┤
│  asyncpg 0.30.0 (Postgres Driver)      │  ← Database Driver
├─────────────────────────────────────────┤
│   PostgreSQL 15 (OLTP Database)        │  ← Persistent Storage
└─────────────────────────────────────────┘
```

### Project Structure
```
backend/
├── app/
│   ├── core/                    # Core configuration
│   │   ├── config.py           # Settings (Pydantic)
│   │   └── security.py         # JWT, password hashing
│   │
│   ├── db/                      # Database layer
│   │   ├── base.py             # Base models & mixins
│   │   ├── session.py          # Async engine & session
│   │   └── init_db.py          # Schema initialization
│   │
│   ├── models/                  # Domain models (ORM)
│   │   ├── core.py             # Identity & master data
│   │   ├── finance.py          # Transactional data
│   │   └── analytics.py        # Jobs & support
│   │
│   ├── schemas/                 # Pydantic schemas (API)
│   │   ├── user.py             # UserCreate, UserResponse
│   │   ├── invoice.py          # InvoiceCreate, InvoiceResponse
│   │   └── payment.py          # PaymentCreate, PaymentResponse
│   │
│   ├── api/                     # API routes
│   │   └── v1/
│   │       ├── auth.py         # Authentication endpoints
│   │       ├── invoices.py     # Invoice CRUD
│   │       └── payments.py     # Payment CRUD
│   │
│   ├── services/                # Business logic
│   │   ├── auth_service.py     # JWT token, password
│   │   ├── invoice_service.py  # Invoice workflow
│   │   └── payment_service.py  # Payment allocation
│   │
│   └── main.py                  # FastAPI app entry point
│
├── alembic/                     # Database migrations
│   ├── versions/               # Migration files
│   │   └── db10dff7c201_*.py
│   └── env.py                  # Alembic configuration
│
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── conftest.py             # Pytest fixtures
│
├── alembic.ini                  # Alembic config file
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Multi-stage build
└── .env                         # Environment variables
```

---

## ✅ Completed: Enterprise Schema Migration

**Migration ID:** `db10dff7c201`  
**Database:** `postgres_application_db` (sme_pulse_oltp)  
**Status:** ✅ Applied and Verified

---

## 📊 Schema Structure

### Core Schema (Identity & Master Data)
- `organizations` - Tenant root entity (7 columns)
- `roles` - System-wide roles (4 columns)
- `users` - Application users (8 columns + multi-tenant)
- `user_roles` - User-role assignments (many-to-many)
- `customers` - AR partners (11 columns)
- `suppliers` - AP partners (11 columns)
- `accounts` - Payment accounts (8 columns)

**Total: 7 tables**

### Finance Schema (Transactional Data)
- `ar_invoices` - Sales invoices (11 columns)
- `ap_bills` - Purchase bills (11 columns)
- `payments` - Cash/bank transactions (10 columns)
- `payment_allocations` - Invoice-payment links (9 columns)
  - **Constraint:** `check_allocation_target_exclusive` (either AR or AP, not both)

**Total: 4 tables**

### Analytics Schema (Jobs & Support)
- `export_jobs` - Background export tasks (8 columns)
- `alerts` - System notifications (9 columns)
- `settings` - Tenant configuration (7 columns)

**Total: 3 tables**

---

## 🔑 Key Features Implemented

### Multi-Tenancy
- All tables (except `organizations` and `roles`) include `org_id` column
- Composite indexes on `(field, org_id)` for tenant-scoped queries
- Automatic tenant isolation via `TenantMixin`

### Audit Trail
- All tables include `created_at` and `updated_at` (UTC timezone)
- Automatic timestamps via `TimestampMixin`

### Relationships
- Foreign keys with `CASCADE` and `RESTRICT` strategies
- Bidirectional relationships via SQLAlchemy ORM
- Proper indexes on foreign key columns

### Data Integrity
- CHECK constraints for business rules (payment allocation exclusivity)
- NOT NULL constraints on critical fields
- Composite unique indexes where needed

---

## 🚀 Migration Commands

### Generate New Migration
```bash
docker compose exec backend alembic revision --autogenerate -m "Description"
```

### Apply Migrations
```bash
docker compose exec backend alembic upgrade head
```

### Rollback Migration
```bash
docker compose exec backend alembic downgrade -1
```

### Check Current Version
```bash
docker compose exec backend alembic current
```

### View Migration History
```bash
docker compose exec backend alembic history
```

---

## 📋 Verification Results

### Schemas Created
```sql
SELECT schema_name FROM information_schema.schemata;
-- analytics, core, finance, public
```

### Tables Summary
- **Core:** 7 tables
- **Finance:** 4 tables  
- **Analytics:** 3 tables
- **Total:** 14 tables

### Sample Table Structure (users)
```sql
\d core.users
-- id, email, password_hash, full_name, status
-- created_at, updated_at, org_id
-- Indexes: PK, email, org_id, composite (email, org_id)
-- Referenced by: user_roles (CASCADE)
```

### Migration Version
```sql
SELECT * FROM alembic_version;
-- db10dff7c201
```

---

## 🛠️ Next Steps

### 1. Seed Initial Data
Create seed scripts for:
- System roles (owner, accountant, cashier)
- Demo organization
- Test users

### 2. Implement Repository Pattern
Create service layer abstractions:
- `UserRepository`, `OrganizationRepository`
- `InvoiceRepository`, `PaymentRepository`
- Transaction management patterns

### 3. Build CRUD Endpoints
Implement FastAPI routers:
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - JWT authentication
- `GET /api/v1/invoices` - List invoices (tenant-scoped)
- `POST /api/v1/payments` - Create payment with allocations

### 4. Add Business Logic
Implement domain services:
- Invoice status transitions (draft → posted → paid)
- Payment allocation algorithm (FIFO, LIFO, manual)
- Overdue invoice detection (alerts)

### 5. Testing
- Unit tests for models
- Integration tests for repositories
- API endpoint tests with pytest

---

## 📚 Model Import Reference

```python
from app.models import (
    # Core
    Organization, Role, User, UserRole,
    Customer, Supplier, Account,
    
    # Finance
    ARInvoice, APBill, Payment, PaymentAllocation,
    
    # Analytics
    ExportJob, Alert, Setting,
    
    # Base
    Base
)
```

---

## ⚙️ Configuration

**Alembic Configuration:**
- Location: `backend/alembic/env.py`
- Metadata: `app.models.Base.metadata`
- URL Source: `app.core.config.settings.DATABASE_URL_SYNC`
- Multi-schema: Enabled (`include_schemas=True`)
- Version Table: `public.alembic_version`

**Database Connection:**
- Host: `postgres_application_db`
- Port: `5433` (external), `5432` (internal)
- Database: `sme_pulse_oltp`
- User: `postgres`

---

## 🎯 Architecture Highlights

### Domain-Driven Design
- Clear separation: Core (identity) → Finance (transactions) → Analytics (support)
- Rich domain models with business logic methods
- Repository pattern ready

### Enterprise Patterns
- Multi-tenancy from day one
- Audit trail on all entities
- Soft delete support (is_active flags)
- Optimistic locking ready (updated_at for version checking)

### Performance Optimization
- Composite indexes for tenant-scoped queries
- Connection pooling (20 pool_size, 10 max_overflow)
- Async SQLAlchemy for high concurrency
- Prepared for read replicas (sync vs async URLs)

---

**Migration Status:** ✅ Complete  
**Tables Created:** 14  
**Constraints:** 12 foreign keys, 1 check constraint  
**Indexes:** 40+ indexes (primary, foreign, composite)

---

## 📖 FastAPI - Kiến Thức Cốt Lõi

### 1. Application Lifecycle (Lifespan Events)

FastAPI sử dụng **lifespan context manager** để quản lý startup/shutdown:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run before handling requests
    print("🚀 Starting application...")
    await initialize_database_schemas()
    
    yield  # Application is running
    
    # Shutdown: Run after all requests are done
    print("🛑 Shutting down...")
    await cleanup_resources()

app = FastAPI(lifespan=lifespan)
```

**Ứng dụng trong SME Pulse:**
- Initialize database schemas (core, finance, analytics)
- Create database connection pools
- Load configuration from environment
- Close database connections on shutdown

---

### 2. Dependency Injection

FastAPI's killer feature - inject dependencies vào route functions:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Database session dependency
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Use in routes
@app.get("/invoices")
async def list_invoices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ARInvoice))
    return result.scalars().all()
```

**Common Dependencies trong SME Pulse:**
- `get_db()` - Database session
- `get_current_user()` - Authenticated user from JWT
- `get_current_org_id()` - Tenant isolation
- `check_permission()` - Role-based access control

---

### 3. Pydantic Schemas (Request/Response Models)

Pydantic validation tự động cho API:

```python
from pydantic import BaseModel, EmailStr, Field
from datetime import date
from decimal import Decimal

class InvoiceCreate(BaseModel):
    invoice_no: str = Field(..., min_length=1, max_length=50)
    customer_id: int = Field(..., gt=0)
    issue_date: date
    due_date: date
    total_amount: Decimal = Field(..., gt=0, decimal_places=2)
    notes: str | None = None

class InvoiceResponse(InvoiceCreate):
    id: int
    status: str
    paid_amount: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # SQLAlchemy 2.0 compatibility
```

**Best Practices:**
- Separate schemas: `Create`, `Update`, `Response`, `InDB`
- Use `Field()` for validation (min, max, regex)
- `from_attributes=True` để convert ORM models → Pydantic
- Type hints cho auto-documentation (Swagger UI)

---

### 4. Async/Await Pattern

FastAPI native support cho async operations:

```python
@app.post("/payments")
async def create_payment(
    payment: PaymentCreate,
    db: AsyncSession = Depends(get_db)
):
    # Async database query
    result = await db.execute(
        select(Account).where(Account.id == payment.account_id)
    )
    account = result.scalar_one_or_none()
    
    # Create payment
    new_payment = Payment(**payment.dict())
    db.add(new_payment)
    await db.flush()  # Get ID without committing
    
    # Process allocations
    for alloc in payment.allocations:
        await process_allocation(db, new_payment.id, alloc)
    
    await db.commit()
    return new_payment
```

**Khi nào dùng async:**
- ✅ Database operations (asyncpg)
- ✅ External API calls (httpx)
- ✅ File I/O operations
- ❌ CPU-bound tasks (use Celery instead)

---

### 5. Middleware & CORS

Middleware xử lý requests trước khi đến routes:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),  # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
@app.middleware("http")
async def add_tenant_context(request: Request, call_next):
    # Extract org_id from JWT token
    org_id = get_org_id_from_token(request)
    request.state.org_id = org_id
    
    response = await call_next(request)
    return response
```

**Middleware trong SME Pulse:**
- CORS: Frontend (React) ở localhost:3000
- Authentication: Verify JWT token
- Tenant Context: Auto-inject org_id
- Logging: Request/response tracking
- Error Handling: Centralized exception handling

---

### 6. Path Operations (HTTP Methods)

RESTful endpoints với decorators:

```python
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])

@router.get("/")  # List all
async def list_invoices(
    skip: int = 0,
    limit: int = 100,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(ARInvoice).where(ARInvoice.org_id == current_user.org_id)
    if status_filter:
        query = query.where(ARInvoice.status == status_filter)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_invoice = ARInvoice(**invoice.dict(), org_id=current_user.org_id)
    db.add(new_invoice)
    await db.commit()
    await db.refresh(new_invoice)
    return new_invoice

@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ARInvoice).where(
            ARInvoice.id == invoice_id,
            ARInvoice.org_id == current_user.org_id  # Tenant isolation
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.patch("/{invoice_id}")
async def update_invoice(
    invoice_id: int,
    updates: InvoiceUpdate,
    db: AsyncSession = Depends(get_db)
):
    # Update logic
    pass

@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    # Soft delete: set is_active = False
    pass
```

---

### 7. Exception Handling

Centralized error handling:

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Database constraint violation",
            "detail": str(exc.orig)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "path": str(request.url)
        }
    )
```

---

### 8. Background Tasks

Chạy tasks sau khi response được gửi:

```python
from fastapi import BackgroundTasks

async def send_invoice_email(invoice_id: int, recipient: str):
    # Send email logic
    await email_service.send(recipient, f"Invoice #{invoice_id} created")

@router.post("/invoices")
async def create_invoice(
    invoice: InvoiceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    new_invoice = ARInvoice(**invoice.dict())
    db.add(new_invoice)
    await db.commit()
    
    # Schedule email after response
    background_tasks.add_task(
        send_invoice_email, 
        new_invoice.id, 
        invoice.customer_email
    )
    
    return new_invoice
```

**Note:** Dùng BackgroundTasks cho lightweight tasks. Với heavy tasks (reports, exports), dùng Celery.

---

### 9. Testing với FastAPI

```python
from fastapi.testclient import TestClient
import pytest

@pytest.fixture
def client():
    return TestClient(app)

def test_create_invoice(client):
    response = client.post(
        "/api/v1/invoices",
        json={
            "invoice_no": "INV-001",
            "customer_id": 1,
            "total_amount": 1000.00
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["invoice_no"] == "INV-001"
```

---

## 📖 SQLAlchemy 2.0 - Async ORM

### 1. Declarative Models (New Style)

SQLAlchemy 2.0 sử dụng `Mapped[]` type annotations:

```python
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}
    
    # Type-safe columns với Mapped[]
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))  # Nullable
    
    # Relationships
    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
```

**Lợi ích:**
- ✅ Type hints cho IDE autocomplete
- ✅ MyPy type checking
- ✅ Better error messages
- ✅ Rõ ràng nullable vs not null

---

### 2. Async Engine & Session

Setup async database connections:

```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://...
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Check connection health
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
)

# Dependency for FastAPI
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

### 3. Querying với select()

SQLAlchemy 2.0 style - luôn dùng `select()`:

```python
from sqlalchemy import select, and_, or_, func

# Simple select
result = await db.execute(select(User).where(User.email == "user@example.com"))
user = result.scalar_one_or_none()

# Join queries
stmt = (
    select(ARInvoice, Customer)
    .join(Customer, ARInvoice.customer_id == Customer.id)
    .where(ARInvoice.org_id == current_user.org_id)
    .order_by(ARInvoice.issue_date.desc())
)
result = await db.execute(stmt)
invoices_with_customers = result.all()

# Aggregate functions
stmt = select(
    func.count(ARInvoice.id).label("total_invoices"),
    func.sum(ARInvoice.total_amount).label("total_amount")
).where(ARInvoice.status == "paid")
result = await db.execute(stmt)
stats = result.one()

# Subqueries
subq = (
    select(Payment.id)
    .where(Payment.amount > 1000)
    .subquery()
)
stmt = select(PaymentAllocation).where(
    PaymentAllocation.payment_id.in_(select(subq))
)
```

---

### 4. Relationships & Eager Loading

Tránh N+1 query problem:

```python
from sqlalchemy.orm import selectinload, joinedload

# Lazy loading (default) - N+1 problem
invoices = await db.execute(select(ARInvoice))
for invoice in invoices.scalars():
    print(invoice.customer.name)  # Triggers separate query per invoice!

# Eager loading với selectinload (separate query, better for collections)
stmt = select(ARInvoice).options(selectinload(ARInvoice.customer))
result = await db.execute(stmt)
invoices = result.scalars().all()  # Only 2 queries total

# Eager loading với joinedload (single query with JOIN)
stmt = select(Payment).options(
    joinedload(Payment.account),
    selectinload(Payment.allocations)
)
result = await db.execute(stmt)
payments = result.unique().scalars().all()  # unique() để remove duplicates from JOIN
```

**Chọn loading strategy:**
- `selectinload()`: Collections (one-to-many) - `user.roles`
- `joinedload()`: Single objects (many-to-one) - `invoice.customer`
- `subqueryload()`: Large collections với complex conditions

---

### 5. Insert/Update/Delete

```python
# Insert single
new_invoice = ARInvoice(
    invoice_no="INV-001",
    customer_id=1,
    total_amount=1000.00,
    org_id=current_user.org_id
)
db.add(new_invoice)
await db.flush()  # Get ID without committing
print(new_invoice.id)  # Available after flush
await db.commit()

# Bulk insert
invoices = [
    ARInvoice(invoice_no=f"INV-{i}", customer_id=1, total_amount=100)
    for i in range(100)
]
db.add_all(invoices)
await db.commit()

# Update
stmt = (
    update(ARInvoice)
    .where(ARInvoice.id == invoice_id)
    .values(status="paid", paid_amount=total_amount)
)
await db.execute(stmt)
await db.commit()

# Delete (soft delete preferred)
stmt = (
    update(Customer)
    .where(Customer.id == customer_id)
    .values(is_active=False)
)
await db.execute(stmt)
```

---

### 6. Transactions

```python
# Auto-commit via get_db() dependency
async def create_payment_with_allocations(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db)  # Auto-commit on success
):
    payment = Payment(**payment_data.dict())
    db.add(payment)
    await db.flush()
    
    for alloc in payment_data.allocations:
        allocation = PaymentAllocation(
            payment_id=payment.id,
            **alloc.dict()
        )
        db.add(allocation)
    
    # Commit happens automatically in get_db()
    return payment

# Manual transaction control
async def complex_operation():
    async with async_session_maker() as session:
        async with session.begin():  # Explicit transaction
            # All operations in this block are atomic
            user = User(email="user@example.com")
            session.add(user)
            await session.flush()
            
            role = UserRole(user_id=user.id, role_id=1)
            session.add(role)
            
            # Auto-commit when exiting context
        # Or auto-rollback on exception
```

---

## 📖 Alembic - Database Migrations

### 1. Alembic Initialization

```bash
# Initialize Alembic (chỉ chạy 1 lần)
alembic init alembic

# Tạo ra:
# alembic/
# ├── env.py           # Configuration
# ├── script.py.mako   # Template for new migrations
# └── versions/        # Migration files
# alembic.ini          # Config file
```

---

### 2. Configuration (env.py)

Cấu hình Alembic để nhận diện models:

```python
# alembic/env.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.models import Base  # Import Base với tất cả models

config = context.config

# Override URL từ environment
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# Metadata từ models
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,  # Multi-schema support
            compare_type=True,     # Compare column types
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

---

### 3. Creating Migrations

```bash
# Autogenerate migration từ models
alembic revision --autogenerate -m "Add customer credit_limit column"

# Tạo empty migration (manual)
alembic revision -m "Create custom index"

# Migration file generated: alembic/versions/xxxxx_add_customer_credit_limit.py
```

**Migration file structure:**

```python
"""Add customer credit_limit column

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2025-11-19 10:30:00

"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123def456'
down_revision = 'previous_revision_id'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Forward migration
    op.add_column(
        'customers',
        sa.Column('credit_limit', sa.Numeric(18, 2), nullable=True),
        schema='core'
    )
    op.create_index(
        'ix_customers_credit_limit',
        'customers',
        ['credit_limit'],
        schema='core'
    )

def downgrade() -> None:
    # Rollback migration
    op.drop_index('ix_customers_credit_limit', table_name='customers', schema='core')
    op.drop_column('customers', 'credit_limit', schema='core')
```

---

### 4. Migration Operations

**Common operations:**

```python
# Add column
op.add_column('users', sa.Column('phone', sa.String(20)), schema='core')

# Drop column
op.drop_column('users', 'phone', schema='core')

# Alter column
op.alter_column(
    'users',
    'email',
    existing_type=sa.String(100),
    type_=sa.String(255),
    schema='core'
)

# Create table
op.create_table(
    'audit_logs',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('action', sa.String(50)),
    sa.Column('timestamp', sa.DateTime(timezone=True)),
    schema='analytics'
)

# Drop table
op.drop_table('audit_logs', schema='analytics')

# Create index
op.create_index(
    'ix_invoices_status_org',
    'ar_invoices',
    ['status', 'org_id'],
    schema='finance'
)

# Create foreign key
op.create_foreign_key(
    'fk_payments_account',
    'payments', 'accounts',
    ['account_id'], ['id'],
    source_schema='finance',
    referent_schema='core',
    ondelete='RESTRICT'
)

# Execute raw SQL
op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

# Data migration
from sqlalchemy import table, column
users_table = table(
    'users',
    column('id', sa.Integer),
    column('status', sa.String)
)
op.execute(
    users_table.update()
    .where(users_table.c.status == None)
    .values(status='active')
)
```

---

### 5. Multi-Schema Support

Alembic với multiple schemas (core, finance, analytics):

```python
# env.py configuration
def run_migrations_online():
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,  # Enable multi-schema
        version_table_schema=None,  # Store alembic_version in public
    )

# Migration file
def upgrade():
    # Create schema first (if not exists)
    op.execute("CREATE SCHEMA IF NOT EXISTS finance")
    
    # Create table in specific schema
    op.create_table(
        'ar_invoices',
        sa.Column('id', sa.Integer, primary_key=True),
        schema='finance'  # Specify schema
    )
```

---

### 6. Migration Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade abc123def456

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade abc123def456

# Show current version
alembic current

# Show migration history
alembic history --verbose

# Show SQL without executing (dry-run)
alembic upgrade head --sql

# Stamp database to specific version (without running migrations)
alembic stamp head
```

---

### 7. Best Practices

**DO:**
- ✅ Review autogenerated migrations before applying
- ✅ Test migrations on staging before production
- ✅ Use transactions for data migrations
- ✅ Add both `upgrade()` and `downgrade()` functions
- ✅ Use descriptive migration messages
- ✅ Keep migrations small and focused

**DON'T:**
- ❌ Edit applied migrations (create new one instead)
- ❌ Delete migration files after applying
- ❌ Mix schema changes with data migrations
- ❌ Forget to handle NULL values when adding NOT NULL columns
- ❌ Use `op.execute()` without proper escaping

---

### 8. Common Patterns

**Add NOT NULL column safely:**

```python
def upgrade():
    # Step 1: Add column as nullable
    op.add_column('users', sa.Column('status', sa.String(20)))
    
    # Step 2: Populate existing rows
    op.execute("UPDATE core.users SET status = 'active' WHERE status IS NULL")
    
    # Step 3: Make it NOT NULL
    op.alter_column('users', 'status', nullable=False, schema='core')

def downgrade():
    op.drop_column('users', 'status', schema='core')
```

**Rename column:**

```python
def upgrade():
    op.alter_column('customers', 'old_name', new_column_name='new_name', schema='core')

def downgrade():
    op.alter_column('customers', 'new_name', new_column_name='old_name', schema='core')
```

**Conditional migration:**

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('users', schema='core')]
    if 'phone' not in columns:
        op.add_column('users', sa.Column('phone', sa.String(20)), schema='core')
```

---

## 🔐 Security Best Practices

### 1. Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### 2. JWT Token

```python
from jose import JWTError, jwt
from datetime import datetime, timedelta

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 3. Protected Routes

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Protected route
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

---

## 🚀 Performance Optimization

### 1. Connection Pooling

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,           # Number of permanent connections
    max_overflow=10,        # Extra connections when pool is full
    pool_timeout=30,        # Wait timeout for connection
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True,     # Test connection before using
)
```

### 2. Query Optimization

```python
# Use indexes
stmt = select(ARInvoice).where(
    ARInvoice.org_id == org_id,  # Indexed
    ARInvoice.status == "overdue"  # Indexed
)

# Limit results
stmt = stmt.limit(100).offset(skip)

# Select specific columns
stmt = select(ARInvoice.id, ARInvoice.invoice_no, ARInvoice.total_amount)

# Use COUNT efficiently
stmt = select(func.count()).select_from(ARInvoice).where(ARInvoice.status == "paid")
```

### 3. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_system_roles() -> list[Role]:
    # Cache system roles (rarely change)
    return db.query(Role).all()
```

---

## 📝 Summary

**Backend Setup Status:**
- ✅ FastAPI application with lifespan management
- ✅ SQLAlchemy 2.0 async ORM with type-safe models
- ✅ Alembic migrations with multi-schema support
- ✅ PostgreSQL database with 14 tables across 3 schemas
- ✅ Docker containerization with health checks
- ✅ Environment-based configuration (Pydantic Settings)
- ✅ Multi-tenancy architecture (org_id isolation)
- ✅ Audit trail (created_at, updated_at)

**Next Implementation Steps:**
1. JWT Authentication & Authorization
2. CRUD endpoints for all entities
3. Business logic services (invoice workflow, payment allocation)
4. Unit & integration tests
5. API documentation (Swagger UI)
6. Background jobs (Celery)
7. Monitoring & logging (Sentry, Prometheus)

## Checking status
PS D:\SinhVien\UIT_HocChinhKhoa\HK1 2025 - 2026\SME pulse project> Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing | Select-Object StatusCode, Content

StatusCode Content        
---------- -------
       200 {"status":"ok"}
