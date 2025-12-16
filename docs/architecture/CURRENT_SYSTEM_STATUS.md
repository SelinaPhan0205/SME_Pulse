# 📊 BÁO CÁO HIỆN TRẠNG HỆ THỐNG SME PULSE

**Ngày tạo:** 16/12/2025 | **Vai trò:** Technical Lead

---

## 1. TỔNG QUAN KIẾN TRÚC

### 1.1 Các Services (docker-compose.yml)

| Service | Image/Build | Port | Vai trò |
|---------|-------------|------|---------|
| **postgres** | postgres:15-alpine | 5432 | Data Lakehouse DB |
| **postgres_application_db** | postgres:15-alpine | 5433 | OLTP Backend DB |
| **redis** | redis:7-alpine | 6379 | Cache |
| **minio** | minio/minio | 9000, 9001 | S3 Data Lake Storage |
| **trino** | Custom build | 8081 | SQL Query Engine (Iceberg) |
| **hive-metastore** | Custom build | 9083 | Iceberg Catalog |
| **airflow-scheduler/webserver** | Custom build | 8080 | Workflow Orchestration |
| **metabase** | metabase/metabase | 3000 | BI & Dashboard |
| **backend** | FastAPI | 8000 | REST API |
| **celery-worker** | Same as backend | - | Background Tasks |

**Đường dẫn:** [docker-compose.yml](docker-compose.yml)

```yaml
# Ví dụ service backend
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
  environment:
    BACKEND_DB_HOST: postgres_application_db
    BACKEND_SECRET_KEY: ${BACKEND_SECRET_KEY}
    MINIO_ENDPOINT: minio:9000
  ports:
    - "${BACKEND_PORT}:8000"
```

### 1.2 Middleware Bảo mật

**Đường dẫn:** [backend/app/middleware/security.py](backend/app/middleware/security.py)

```python
# 3 Middleware chính
class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing to all requests."""
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers: X-Content-Type-Options, X-Frame-Options, etc."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiter for login endpoint (max 5 requests/60s)."""
    def __init__(self, app, max_requests=5, window_seconds=60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
```

**Đường dẫn:** [backend/app/main.py](backend/app/main.py) (line 44-57)

```python
# App Initialization
app = FastAPI(
    title="SME Pulse Backend",
    version="1.0.0",
    docs_url="/api/docs",      # Swagger UI
    redoc_url="/api/redoc",    # ReDoc
)

# Add Security Middlewares (order matters!)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/v1", tags=["User Management"])
app.include_router(finance_router, prefix="/api/v1", tags=["Finance"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
```

### 1.3 External Data Sources (New in Phase 4)

**Đường dẫn:** [EXTERNAL_DATA_INTEGRATION.md](EXTERNAL_DATA_INTEGRATION.md)

Hệ thống tích hợp 2 nguồn dữ liệu bên ngoài:

| Nguồn | API | Tần suất | Dữ liệu | Mục đích |
|-------|-----|----------|---------|---------|
| **World Bank** | `api.worldbank.org` | Hàng năm | GDP, CPI, Unemployment | Macro-economic context |
| **Vietnam Provinces** | `provinces.open-api.vn` | Hàng tháng | 63 tỉnh + 691 huyện | Geographic hierarchy |

**Kiến trúc:** Bronze (MinIO) → Silver (dbt stg_*) → Gold (dbt dim_macro_indicators, dim_location)

**File Script:**
- [ops/external_sources/ingest_world_bank.py](ops/external_sources/ingest_world_bank.py) - Fetch từ World Bank API
- [ops/external_sources/ingest_provinces.py](ops/external_sources/ingest_provinces.py) - Fetch từ Provinces API

---

## 2. THIẾT KẾ CƠ SỞ DỮ LIỆU

### 2.1 Cấu trúc Models

**Đường dẫn:** `backend/app/models/`

| File | Schema | Entities |
|------|--------|----------|
| `core.py` | core | Organization, User, Role, UserRole, Customer, Supplier, Account |
| `finance.py` | finance | ARInvoice, APBill, Payment, PaymentAllocation |
| `analytics.py` | analytics | ExportJob, Alert, Setting |

### 2.2 Các Thực thể Chính

**Đường dẫn:** [backend/app/models/core.py](backend/app/models/core.py)

```python
class User(Base, TimestampMixin, TenantMixin):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")
    # Multi-tenancy: org_id từ TenantMixin
```

**Đường dẫn:** [backend/app/models/finance.py](backend/app/models/finance.py)

```python
class ARInvoice(Base, TimestampMixin, TenantMixin):
    __tablename__ = "ar_invoices"
    __table_args__ = {"schema": "finance"}
    
    invoice_no: Mapped[str] = mapped_column(String(50), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("core.customers.id"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # status: draft, posted, paid, overdue, cancelled

class Payment(Base, TimestampMixin, TenantMixin):
    __tablename__ = "payments"
    __table_args__ = {"schema": "finance"}
    
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))  # cash, transfer, vietqr
```

### 2.3 Bảng lưu kết quả AI/ML

**Đường dẫn:** [dbt/models/gold/ml_scores/](dbt/models/gold/ml_scores/)

| Table (Trino) | Mục đích |
|---------------|----------|
| `gold.ml_cashflow_forecast` | Kết quả dự báo Prophet |
| `gold.ml_anomaly_alerts` | Kết quả phát hiện bất thường |
| `gold.ml_ar_priority_scores` | Điểm ưu tiên thu nợ |

---

## 3. THIẾT KẾ API & BACKEND

### 3.0 Sơ đồ Kiến trúc Backend (Simplified Clean Architecture)

```plantuml
@startuml
package "Presentation Layer" {
    interface AuthRouter as AR {
        /auth/login
        /auth/me
    }
    interface FinanceRouter as FR {
        /api/v1/invoices
        /api/v1/payments
    }
    interface AnalyticsRouter as ANR {
        /api/v1/analytics/summary
        /api/v1/analytics/forecast
        /api/v1/analytics/anomalies
    }
}

package "Service Layer" {
    class AuthService {
        +authenticate_user()
        +create_token()
    }
    class FinanceService {
        +create_invoice()
        +create_payment()
        +allocate_payment()
    }
    class AnalyticsService {
        +get_dashboard()
        +calculate_kpi()
        +get_forecast()
    }
}

package "Domain Models" {
    class Organization {
        -id: int
        -name: string
        -tax_code: string
    }
    class User {
        -id: int
        -email: string
        -password_hash: string
        -org_id: int
    }
    class Customer {
        -id: int
        -name: string
        -credit_term: int
        -org_id: int
    }
    class Supplier {
        -id: int
        -name: string
        -org_id: int
    }
    class ARInvoice {
        -id: int
        -invoice_no: string
        -customer_id: int
        -total_amount: decimal
        -paid_amount: decimal
        -status: string
        -org_id: int
    }
    class APBill {
        -id: int
        -bill_no: string
        -supplier_id: int
        -total_amount: decimal
        -org_id: int
    }
    class Payment {
        -id: int
        -amount: decimal
        -payment_method: string
        -org_id: int
    }
}

package "Infrastructure" {
    class SecurityService {
        +verify_password()
        +create_jwt()
    }
    class Database {
        PostgreSQL
        AsyncSession
    }
    class TrinoEngine {
        Query ML Tables
        Gold Layer
    }
}

AR --> AuthService : uses
FR --> FinanceService : uses
ANR --> AnalyticsService : uses

AuthService --> SecurityService : uses
AuthService --> Database : uses
AuthService --> User : operates

FinanceService --> Database : uses
FinanceService --> ARInvoice : creates/operates
FinanceService --> APBill : operates
FinanceService --> Payment : operates

AnalyticsService --> Database : uses
AnalyticsService --> TrinoEngine : queries
AnalyticsService --> ARInvoice : queries
AnalyticsService --> Payment : queries

Organization "1" --* "many" User : contains
Organization "1" --* "many" Customer : contains
Organization "1" --* "many" ARInvoice : contains
Customer "1" --* "many" ARInvoice : issues
Supplier "1" --* "many" APBill : sends
Payment "many" -* "many" ARInvoice : allocates
Payment "many" -* "many" APBill : allocates

@enduml
```

**Kiến trúc 3 lớp (Clean Architecture):**

| Layer | Components | Trách nhiệm |
|-------|-----------|-------------|
| **🌐 Routers** | AuthRouter, FinanceRouter, AnalyticsRouter | HTTP endpoints, request validation |
| **⚙️ Services** | AuthService, FinanceService, AnalyticsService | Business logic, orchestration |
| **💾 Models** | User, ARInvoice, APBill, Payment, Customer | Domain entities, database tables |
| **🔧 Infrastructure** | SecurityService, Database, Trino | Cross-cutting concerns, external systems |

**Flow xử lý request:**

```
1. Client → AuthRouter.login()
2. AuthRouter → AuthService.authenticate_user()
3. AuthService → Database (query User)
4. AuthService → SecurityService.verify_password()
5. AuthService → SecurityService.create_jwt()
6. AuthRouter → Client (return token)
```

**Multi-tenancy:**
- Tất cả models có `org_id` để isolation
- Mỗi request validate JWT chứa `org_id`
- Database queries tự động filter theo `org_id`

**Design Patterns:**
- **Clean Architecture**: Routers → Services → Models
- **Dependency Injection**: FastAPI Depends()
- **Repository Pattern**: Services đóng gói DB operations

### 3.1 Cấu trúc Modules (Clean Architecture)

```
backend/app/
├── core/
│   ├── config.py           # Settings, JWT, DB connection
│   ├── security.py         # Password hash, JWT encode/decode
│   ├── logging_config.py
│   ├── celery_config.py    # Celery worker for async tasks
│   └── exceptions.py       # Custom exception classes
├── db/
│   ├── base.py             # Base model, mixins (TenantMixin, TimestampMixin)
│   ├── session.py          # Async session factory
│   └── init_db.py          # Schema initialization
├── models/                 # ORM models (SQLAlchemy)
│   ├── core.py             # Organization, User, Customer, Supplier, Account
│   ├── finance.py          # ARInvoice, APBill, Payment, PaymentAllocation
│   └── analytics.py        # ExportJob, Alert, Setting
├── schema/                 # Pydantic schemas (request/response validation)
│   ├── auth/               # LoginRequest, LoginResponse, ChangePasswordRequest
│   ├── finance/            # InvoiceCreate, PaymentCreate, etc.
│   └── analytics/          # DashboardSummary, ForecastResponse, etc.
├── modules/                # Business logic layer
│   ├── auth/
│   │   ├── router.py       # @router.post("/login")
│   │   ├── service.py      # authenticate_user(), create_user_token()
│   │   └── dependencies.py # get_current_user(), requires_roles()
│   ├── finance/
│   │   ├── router.py       # AR/AP/Payment endpoints
│   │   ├── service.py      # Business logic for finance
│   │   └── services/       # Specific services (ar_service, payment_service)
│   ├── analytics/
│   │   ├── router.py       # Dashboard, Forecast, Anomaly endpoints
│   │   ├── service.py      # KPI calculations, Trino queries
│   │   ├── schemas.py      # Response models
│   │   ├── tasks.py        # Celery tasks for async operations
│   │   └── services/       # Specific services (aging_service, kpi_service)
│   ├── users/              # User management
│   ├── partners/           # Customers & Suppliers
│   └── settings/           # System settings
├── middleware/
│   ├── security.py         # RequestContext, SecurityHeaders, RateLimit
│   └── __init__.py
└── main.py                 # FastAPI app initialization
```

**Mô hình Clean Architecture:**

```
Request → Router → Service → Model/Database
           ↓
        Dependencies (JWT, DB session)
           ↓
        Security checks
```

### 3.2 Luồng xử lý API Dự báo Dòng tiền (UC09 - Prophet Forecast)

```plantuml
@startuml
autonumber
actor User
participant React
participant Hook as "useRevenueForecast"
participant Axios
participant Router as "AnalyticsRouter"
participant Auth as "AuthCheck"
participant Service as "AnalyticsService"
participant Cache as "Redis"
participant Trino
participant Iceberg
participant Chart

User -> React: Click "Xem dự báo dòng tiền"
activate React

React -> Hook: useRevenueForecast(start_date, end_date)
activate Hook
note right of Hook
  React Query checks cache
  staleTime: 30 min
end note

Hook -> Axios: GET /api/v1/analytics/forecast/revenue
activate Axios
note right of Axios
  Attach JWT token
  Authorization: Bearer ...
end note

Axios -> Router: GET /api/v1/analytics/forecast/revenue
activate Router

Router -> Auth: Validate JWT
activate Auth
note right of Auth
  decode_access_token()
  Verify org_id, roles, expiry
end note
Auth --> Router: Current User (org_id=1)
deactivate Auth

Router -> Service: get_revenue_forecast(db, org_id, ...)
activate Service

Service -> Cache: Check key "forecast:org_1:..."
activate Cache

alt Cache HIT
  Cache --> Service: Cached data (JSON)
  note right of Service
    Return from cache
    Time: ~5ms
  end note
else Cache MISS
  Cache --> Service: No cache
  deactivate Cache
  
  Service -> Trino: Connect to Trino (catalog=sme_lake)
  activate Trino
  
  Service -> Trino: Execute SQL SELECT
  note right of Trino
    SELECT forecast_date, predicted_cashflow,
    lower_bound, upper_bound
    FROM gold.ml_cashflow_forecast
    WHERE forecast_date BETWEEN '2025-01-01'
    AND '2025-01-31'
  end note
  
  Trino -> Iceberg: Read Parquet files from MinIO
  activate Iceberg
  Iceberg --> Trino: Return forecast rows (31 rows)
  deactivate Iceberg
  
  Trino --> Service: Result data
  deactivate Trino
  
  Service -> Service: Transform to JSON
  note right of Service
    {data: [{date, forecast, lower, upper}]}
  end note
  
  Service -> Cache: Store in Redis (TTL=30 min)
  activate Cache
  Cache --> Service: OK
  deactivate Cache
end

Service --> Router: ForecastResponse JSON
deactivate Service

Router --> Axios: HTTP 200 OK
deactivate Router

Axios --> Hook: Response data
deactivate Axios

Hook -> Hook: React Query caches response
note right of Hook
  staleTime: 30 min
end note
Hook --> React: {data, isLoading: false}
deactivate Hook

React -> Chart: Render ForecastChart
activate Chart

Chart -> Chart: Transform for Recharts
note right of Chart
  Confidence interval (shaded)
  Forecast line (dashed)
  Actual line (solid)
end note

Chart --> User: Display forecast chart
deactivate Chart
deactivate React

note over User,Chart
  Total: ~400ms (cache miss)
  Total: ~50ms (cache hit)
end note

@enduml
```

**Giải thích các bước:**

| Bước | Component | Hành động | Thời gian |
|------|-----------|-----------|-----------|
| 1 | React | User click button "Xem dự báo" | - |
| 2 | useRevenueForecast | React Query check cache trong memory | ~1ms |
| 3 | Axios | Attach JWT token vào header | ~2ms |
| 4 | Router | Nhận request, route tới handler | ~5ms |
| 5 | AuthDependencies | Validate JWT, check org_id, roles | ~10ms |
| 6 | Service | Check Redis cache | ~5ms |
| 7a | Service (HIT) | Return cached data | ~5ms |
| 7b | Service (MISS) | Connect Trino | ~20ms |
| 8 | Trino | Execute SQL query trên Iceberg | ~300ms |
| 9 | Iceberg | Read Parquet từ MinIO | ~250ms |
| 10 | Service | Transform data to JSON | ~10ms |
| 11 | Service | Store in Redis cache (TTL=30 min) | ~5ms |
| 12 | Router | Return HTTP 200 OK | ~5ms |
| 13 | Hook | React Query cache response | ~2ms |
| 14 | Chart | Render Recharts AreaChart | ~20ms |

**Cache Strategy:**

```
Level 1: React Query (Browser memory)
- staleTime: 30 minutes
- refetchOnMount: false
- Purpose: Avoid redundant API calls

Level 2: Redis (Backend cache)
- TTL: 30 minutes
- Key pattern: forecast:org_{org_id}:{start_date}:{end_date}
- Purpose: Avoid expensive Trino queries

Level 3: Trino Query Result Cache
- Automatic caching by Trino coordinator
- Purpose: Optimize repeated identical queries
```

**Error Handling:**

```
1. JWT expired (401) → Redirect to /login
2. Insufficient permissions (403) → Show "Access Denied"
3. Trino timeout (>40s) → Return cached stale data (if available)
4. Iceberg table not found → Return empty forecast + alert admin
5. Network error → React Query retry (max 3 attempts)
```

### 3.3 Clean Architecture Flow: Router → Service → Model

**Ví dụ UC01 Login:**

**Step 1 - Router:** [backend/app/modules/auth/router.py](backend/app/modules/auth/router.py)
```python
@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await authenticate_user(db, credentials.email, credentials.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    user, roles = result
    access_token, expires_in = create_user_token(user.id, user.org_id, roles)
    return LoginResponse(access_token=access_token, user=UserInfo(...), roles=roles)
```

**Step 2 - Service:** [backend/app/modules/auth/service.py](backend/app/modules/auth/service.py)
```python
async def authenticate_user(db: AsyncSession, email: str, password: str):
    stmt = select(User).options(selectinload(User.roles)).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.password_hash):
        return None
    if user.status != "active":
        return None
    
    roles = [ur.role.code for ur in user.roles]
    return user, roles
```

**Step 3 - Security:** [backend/app/core/security.py](backend/app/core/security.py)
```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.BACKEND_SECRET_KEY, algorithm=settings.BACKEND_ALGORITHM)
```

### 3.3 API Routes Chi tiết

**Đường dẫn:** [backend/app/modules/auth/router.py](backend/app/modules/auth/router.py)

```python
# Authentication Endpoints
POST   /auth/login
       Request:  { email: string, password: string }
       Response: { access_token: string, user: UserInfo, roles: [string] }
       Status:   401 if invalid credentials, 422 if validation error

GET    /auth/me
       Response: { id, email, full_name, org_id, status, roles }
       Requires: JWT token
       Status:   401 if token invalid/expired

POST   /auth/change-password
       Request:  { old_password: string, new_password: string }
       Status:   400 if old password wrong, 422 if weak password
```

**Đường dẫn:** [backend/app/modules/analytics/router.py](backend/app/modules/analytics/router.py)

```python
# Analytics Endpoints (UC08-10)
GET    /api/v1/analytics/summary
       Response: { dso, dpo, ccc, total_ar, total_ap, cash_balance, working_capital }
       Purpose:  Dashboard KPI summary
       Requires: JWT + org_id

GET    /api/v1/analytics/aging/ar
       Response: { total_ar, total_invoices, buckets: [{bucket_days, count, total}] }
       Purpose:  AR aging report (0-30, 31-60, 61-90, >90)

GET    /api/v1/analytics/aging/ap
       Response: { total_ap, total_bills, buckets }
       Purpose:  AP aging report

GET    /api/v1/analytics/kpi/daily-revenue?days=7
       Response: { total_revenue, average_daily_revenue, data: [{date, amount}] }
       Purpose:  Daily revenue trend

GET    /api/v1/analytics/forecast/revenue?start_date=2025-01-01&end_date=2025-12-31
       Response: { model_name, data: [{date, forecast, lower_bound, upper_bound}] }
       Purpose:  Prophet cashflow forecast from Trino

GET    /api/v1/analytics/anomalies?severity=CRITICAL
       Response: { data: [{date, amount, anomaly_score, severity}] }
       Purpose:  Isolation Forest anomalies from Trino
       
POST   /api/v1/analytics/export?report_type=ar_report&format=xlsx
       Response: { job_id: string, status: string, file_url: string }
       Purpose:  Create background export job (Celery)
```

**Đường dẫn:** [backend/app/modules/finance/router.py](backend/app/modules/finance/router.py)

```python
# Finance Endpoints (UC03-07)
GET    /api/v1/invoices
       Filters:  ?customer_id=1&status=paid&date_from=2025-01-01
       Response: { items: [InvoiceDetail], total_count, page }
       Purpose:  AR invoices list

POST   /api/v1/invoices
       Request:  { customer_id, invoice_no, issue_date, due_date, total_amount }
       Response: { id, invoice_no, status }
       Purpose:  Create AR invoice

GET    /api/v1/bills
       Response: Similar to invoices but for AP bills

POST   /api/v1/payments
       Request:  { account_id, amount, payment_method, allocations: [{invoice_id, amount}] }
       Response: { id, status, allocations }
       Purpose:  Create payment + allocate to invoices/bills
```

**Đường dẫn:** [backend/app/modules/auth/dependencies.py](backend/app/modules/auth/dependencies.py)

```python
# Dependency Injection Helpers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate JWT token, return authenticated User"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    user_id = int(payload.get("sub"))
    user = await db.execute(select(User).where(User.id == user_id))
    if not user or user.status != "active":
        raise HTTPException(401, "Inactive user")
    # Multi-tenancy: Verify token org_id matches user org_id
    if payload.get("org_id") != user.org_id:
        raise HTTPException(401, "Org mismatch")
    return user

def requires_roles(allowed_roles: List[str]):
    """RBAC decorator for role-based authorization"""
    async def role_checker(current_user = Depends(get_current_user)):
        user_roles = [ur.role.code for ur in current_user.roles]
        if not any(r in allowed_roles for r in user_roles):
            raise HTTPException(403, f"Required: {allowed_roles}")
        return current_user
    return role_checker

# Usage in router:
@router.get("/admin-only", dependencies=[Depends(requires_roles(["owner", "admin"]))])
async def admin_endpoint(current_user: User = Depends(get_current_user)):
    return {"admin_data": "..."}
```

### 3.4 Code gọi AI Model (Prophet/Isolation Forest)

**Đường dẫn:** [backend/app/modules/analytics/service.py](backend/app/modules/analytics/service.py) (line 210-280)

**UC09 - Prophet Cashflow Forecast:**
```python
def _get_trino_connection():
    """Connect to Trino for querying ML Gold tables."""
    TRINO_TIMEOUT = int(os.getenv("TRINO_TIMEOUT", "40"))
    return trino.dbapi.connect(
        host=os.getenv("TRINO_HOST", "trino"),
        port=int(os.getenv("TRINO_PORT", 8080)),
        user="api_backend",
        catalog="sme_lake",
        schema="gold",
        request_timeout=TRINO_TIMEOUT,  # 40s to allow complex queries
    )

async def get_revenue_forecast(db, org_id, start_date=None, end_date=None):
    """
    UC09: Query sme_lake.gold.ml_cashflow_forecast created by weekly training job
    
    Model Details:
    - Algorithm: Facebook Prophet (time series forecasting with seasonality)
    - Training Data: 90 days historical payments from silver.ml_training_cashflow_fcst
    - Regressors: is_weekend, is_holiday_vn, is_beginning_of_month, sin_month, cos_month
    - Retraining: Weekly (Sunday 1:00 AM) via sme_pulse_ml_training DAG
    - Output: 30-day forecast with 95% confidence intervals
    - Accuracy Metric: MAPE (Mean Absolute Percentage Error) < 10%
    """
    try:
        conn = _get_trino_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT 
            forecast_date,
            predicted_cashflow,
            lower_bound,    -- 2.5 percentile
            upper_bound,    -- 97.5 percentile (95% CI)
            model_name,
            prediction_timestamp
        FROM sme_lake.gold.ml_cashflow_forecast
        WHERE forecast_date >= DATE '{start_date.isoformat()}' 
          AND forecast_date <= DATE '{end_date.isoformat()}'
        ORDER BY forecast_date ASC
        """
        
        cursor.execute(query)
        results = []
        for row in cursor.fetchall():
            results.append({
                "date": row[0].isoformat(),
                "forecast": float(row[1]),      # Predicted value
                "lower_bound": float(row[2]),   # Conservative estimate
                "upper_bound": float(row[3]),   # Optimistic estimate
            })
        
        cursor.close()
        conn.close()
        return results
        
    except Exception as e:
        logger.warning(f"Trino unavailable, using PostgreSQL fallback: {e}")
        # Fallback: Generate synthetic forecast based on historical average + variance
        return await _generate_forecast_fallback(db, org_id, start_date, end_date)
```

**UC10 - Isolation Forest Anomalies:**
```python
async def get_revenue_anomalies(db, org_id, start_date=None, end_date=None, severity=None):
    """
    UC10: Query sme_lake.gold.ml_anomaly_alerts created by weekly training job
    
    Model Details:
    - Algorithm: Isolation Forest (unsupervised outlier detection)
    - Training Data: 180 days bank transactions from gold.fact_bank_txn
    - Features: amount, direction, category, recency, frequency, day_of_week, etc.
    - Contamination Rate: 5% (assumes 5% of transactions are anomalies)
    - Retraining: Weekly (Sunday 1:00 AM)
    - Output: Anomaly score (0-1, >0.5 = anomaly) + severity label
    - Severity Levels: CRITICAL, HIGH, MEDIUM, LOW
    """
    try:
        conn = _get_trino_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT 
            txn_date,
            amount_vnd,
            anomaly_score,       -- Isolation Forest score (0-1)
            severity,            -- CRITICAL | HIGH | MEDIUM | LOW
            transaction_category, -- RECEIVABLE | PAYABLE | PAYROLL | OTHER
            counterparty_name
        FROM sme_lake.gold.ml_anomaly_alerts
        WHERE 1=1
        """
        
        if start_date:
            query += f" AND txn_date >= DATE '{start_date.isoformat()}'"
        if end_date:
            query += f" AND txn_date <= DATE '{end_date.isoformat()}'"
        if severity:
            query += f" AND severity = '{severity.upper()}'"
        
        query += " ORDER BY anomaly_score DESC LIMIT 1000"
        
        cursor.execute(query)
        results = []
        for row in cursor.fetchall():
            results.append({
                "date": row[0].isoformat(),
                "amount": float(row[1]),
                "deviation": float(row[2]),     # anomaly_score
                "severity": row[3],
                "category": row[4],
                "counterparty": row[5],
            })
        
        return results
```

**Storage & Training:**
- **Model Storage**: MLflow at `/tmp/airflow_mlflow` (mounted volume)
- **Forecast Table**: `sme_lake.gold.ml_cashflow_forecast` (Iceberg)
- **Anomaly Table**: `sme_lake.gold.ml_anomaly_alerts` (Iceberg)
- **Training Scripts**:
  - [ops/ml/UC09-forecasting/train_cashflow_model.py](ops/ml/UC09-forecasting/train_cashflow_model.py)
  - [ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/train_isolation_forest.py](ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/train_isolation_forest.py)
- **Orchestration**: [airflow/dags/sme_pulse_ml_training.py](airflow/dags/sme_pulse_ml_training.py)

---

## 4. GIAO DIỆN FRONTEND

### 4.1 Cấu trúc Pages & Components

```
frontend/src/
├── pages/
│   └── DashboardLayout.tsx     # Main layout wrapper
├── components/
│   ├── Dashboard.tsx           # UC08: Main dashboard page
│   ├── Login.tsx              # UC01: Login page
│   ├── Sidebar.tsx            # Navigation with role-based filtering
│   ├── UserMenu.tsx           # User profile dropdown
│   ├── Forecast.tsx           # UC09: Prophet forecast detail page
│   ├── ForecastChart.tsx      # 7-day forecast chart component
│   ├── ForecastDetailChart.tsx # 30/90-day detail chart with MAPE metrics
│   ├── AnomalyDetection.tsx   # UC10: Anomaly alerts detail page
│   ├── AnomalyChart.tsx       # Isolation Forest results visualization
│   ├── AccountsReceivable.tsx # UC05: AR aged debt, customer view
│   ├── AccountsPayable.tsx    # UC06: AP aged debt, supplier view
│   ├── Payments.tsx           # UC07: Payment list, create, VietQR QR code
│   ├── Reports.tsx            # UC02: Excel export, summary reports
│   ├── UserManagement.tsx     # Admin: User CRUD, roles
│   ├── Settings.tsx           # System settings
│   └── ui/                    # Shadcn components (Card, Button, Tabs, etc.)
├── lib/api/
│   ├── client.ts              # Axios instance with auth interceptors
│   ├── types.ts               # TypeScript interfaces for API responses
│   ├── index.ts               # API client exports
│   ├── services/
│   │   └── analyticsAPI.ts    # Fetch dashboard, forecast, anomalies
│   └── hooks/
│       ├── useAnalytics.ts    # useRevenueForecast, useRevenueAnomalies, etc.
│       ├── useAuth.ts         # useLogin, useLogout, useCurrentUser
│       ├── useInvoices.ts     # useARInvoices, useAPBills
│       └── usePayments.ts     # usePayments, useCreatePayment
├── contexts/
│   └── SidebarContext.tsx     # Mobile sidebar open/close state
├── lib/
│   └── permissions.ts         # RBAC helpers: hasMenuAccess, getUserRoles
└── vite.config.ts             # Vite build config
```

### 4.2 Frontend Pages & Routes

**Đường dẫn:** [frontend/src/components/Sidebar.tsx](frontend/src/components/Sidebar.tsx)

```tsx
// Menu items with role-based filtering
const allMenuItems = [
  { id: 'dashboard', label: 'Dashboard', path: '/dashboard', roles: ['all'] },
  { id: 'debt', label: 'Công nợ', hasSubmenu: true, roles: ['accountant', 'owner']
    submenu: [
      { id: 'ar', label: 'Công nợ phải thu', path: '/dashboard/ar' },
      { id: 'ap', label: 'Công nợ phải trả', path: '/dashboard/ap' },
    ]
  },
  { id: 'payment', label: 'Thanh toán', path: '/dashboard/payments', roles: ['accountant', 'cashier'] },
  { id: 'forecast', label: 'Dự báo dòng tiền', path: '/dashboard/forecast', roles: ['owner', 'accountant'] },
  { id: 'anomaly', label: 'Cảnh báo bất thường', path: '/dashboard/anomaly', roles: ['owner'] },
  { id: 'report', label: 'Báo cáo', path: '/dashboard/reports', roles: ['accountant', 'owner'] },
  { id: 'user', label: 'Quản lý người dùng', path: '/dashboard/users', roles: ['owner'] },
  { id: 'settings', label: 'Cài đặt hệ thống', path: '/dashboard/settings', roles: ['owner'] },
];

// Filter based on user roles
const visibleMenuItems = allMenuItems.filter(item => 
  item.roles.includes('all') || hasMenuAccess(userRoles, item.id)
);
```

**Route Mapping:**

| Route | Component | Role | UC |
|-------|-----------|------|-----|
| `/login` | Login.tsx | Public | UC01 |
| `/dashboard` | Dashboard.tsx | accountant+ | UC08 |
| `/dashboard/ar` | AccountsReceivable.tsx | accountant+ | UC05 |
| `/dashboard/ap` | AccountsPayable.tsx | accountant+ | UC06 |
| `/dashboard/payments` | Payments.tsx | cashier+ | UC07 |
| `/dashboard/forecast` | Forecast.tsx | accountant+ | UC09 |
| `/dashboard/anomaly` | AnomalyDetection.tsx | owner | UC10 |
| `/dashboard/reports` | Reports.tsx | accountant+ | UC02 |
| `/dashboard/users` | UserManagement.tsx | owner | - |
| `/dashboard/settings` | Settings.tsx | owner | - |

**Đường dẫn:** [frontend/src/components/Login.tsx](frontend/src/components/Login.tsx)

```tsx
export default function Login() {
  const loginMutation = useLogin();
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Call backend API /auth/login
      const result = await loginMutation.mutateAsync({
        email: formData.email,
        password: formData.password,
      });
      
      // Store JWT token
      localStorage.setItem('token', result.access_token);
      setUserRoles(result.roles);  // Store for RBAC
      
      // Redirect to dashboard
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="email" name="email" placeholder="Email" />
      <input type="password" name="password" placeholder="Password" />
      <button type="submit">Đăng nhập</button>
    </form>
  );
}
```

### 4.3 Data Fetching Architecture (React Query + Axios)

**Đường dẫn:** [frontend/src/components/Dashboard.tsx](frontend/src/components/Dashboard.tsx)

```tsx
export function Dashboard() {
  // React Query hooks để fetch data
  const { data: summary, isLoading: loadingSummary } = useDashboardSummary();
  const { data: paymentRate } = usePaymentSuccessRate();
  const { data: alertsData, isLoading: loadingAlerts } = useAlerts({ status: 'new' });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30">
      {/* Header với UserMenu */}
      <header>...</header>
      
      {/* Metrics Grid - 3 KPI cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {loadingSummary ? <Skeleton /> : metrics.map(m => <Card key={m.title}>...</Card>)}
      </div>
      
      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RevenueChart />   {/* Doanh thu 14 ngày */}
          <ForecastChart />  {/* Dự báo 7 ngày */}
        </div>
        <div>
          {/* Cảnh báo AI */}
          {anomalies.map(a => <AlertCard key={a.id} />)}
        </div>
      </div>
    </div>
  );
}
```

### 4.3 Data Fetching Architecture - Detailed (React Query + Axios)

#### Axios Client Configuration
**Đường dẫn:** [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts)

```typescript
import axios from 'axios';

// Create axios instance with base URL & timeout
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 60000,  // 60s timeout (Trino queries can take 40s)
});

// Request Interceptor: Auto-attach JWT token from localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  console.log(`📤 API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
}, (error) => {
  console.error('Request Error:', error);
  return Promise.reject(error);
});

// Response Interceptor: Handle 401 & other errors
apiClient.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.statusText}`);
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token expired/invalid → Clear localStorage & redirect to login
      console.warn('🔐 Token expired, redirecting to login');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    } else if (error.response?.status === 403) {
      console.error('❌ Access Denied (Forbidden)');
    } else if (error.response?.status >= 500) {
      console.error('❌ Server Error:', error.response.status);
    }
    return Promise.reject(error);
  }
);
```

#### React Query Hooks Pattern
**Đường dẫn:** [frontend/src/lib/api/hooks/useAnalytics.ts](frontend/src/lib/api/hooks/useAnalytics.ts)

```typescript
import { useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '../api';

// Hook 1: Dashboard Summary (Frequently updated)
export function useDashboardSummary() {
  return useQuery({
    queryKey: ['analytics', 'dashboard-summary'],
    queryFn: () => analyticsAPI.getDashboardSummary(),
    staleTime: 60 * 1000,                    // Cache 1 minute
    refetchInterval: 5 * 60 * 1000,         // Auto-refetch every 5 min
  });
}

// Hook 2: Revenue Forecast (Stable forecast)
export function useRevenueForecast(params?: DateRangeParams) {
  return useQuery({
    queryKey: ['analytics', 'revenue-forecast', params],
    queryFn: () => analyticsAPI.getRevenueForecast(params),
    staleTime: 30 * 60 * 1000,  // Cache 30 min (updated weekly only)
    enabled: !!params,           // Don't fetch until params ready
  });
}

// Hook 3: Anomalies (Real-time alerts)
export function useRevenueAnomalies(filters?: AnomalyFilters) {
  return useQuery({
    queryKey: ['analytics', 'anomalies', filters],
    queryFn: () => analyticsAPI.getAnomalies(filters),
    staleTime: 5 * 60 * 1000,   // Cache 5 minutes (real-time concern)
    refetchInterval: 30 * 1000,  // Poll every 30 seconds
  });
}

// Hook 4: AR Invoices with Pagination
export function useARInvoices(page: number, pageSize: number) {
  return useQuery({
    queryKey: ['finance', 'ar-invoices', page, pageSize],
    queryFn: () => financeAPI.getARInvoices({ page, page_size: pageSize }),
    staleTime: 1 * 60 * 1000,   // Cache 1 minute (users create frequently)
    keepPreviousData: true,      // Keep previous page while fetching new
  });
}
```

**Cache Strategy:**
```
KPI/Dashboard:      staleTime=60s   (updated nightly, OK if slightly stale)
Forecasts:          staleTime=30m   (updated weekly, stable)
Anomalies:          staleTime=5m    (critical, needs freshness)
AR/AP Lists:        staleTime=1m    (users edit frequently)
Master Data:        staleTime=1h    (stable, rarely changes)
```

#### React Query Hook Usage in Components
**Đường dẫn:** [frontend/src/lib/api/hooks/useAuth.ts](frontend/src/lib/api/hooks/useAuth.ts)

```typescript
// Authentication hooks
export function useLogin() {
  const navigate = useNavigate();
  const setUser = useSetAtom(userAtom);  // Jotai state
  
  return useMutation({
    mutationFn: (credentials: LoginRequest) => 
      apiClient.post('/auth/login', credentials).then(r => r.data),
    onSuccess: (data) => {
      // Save token & user to localStorage
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      setUser(data.user);
      
      // Redirect to dashboard
      navigate('/dashboard');
    },
    onError: (error: AxiosError) => {
      console.error('Login failed:', error.response?.data);
      // Show toast with error message
    },
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ['auth', 'current-user'],
    queryFn: () => apiClient.get('/auth/me').then(r => r.data),
    staleTime: 10 * 60 * 1000,
    retry: 1,
    retryDelay: 1000,
  });
}
```

### 4.4 Dashboard Component with Full Data Flow

**Đường dẫn:** [frontend/src/components/Dashboard.tsx](frontend/src/components/Dashboard.tsx)

```tsx
export function Dashboard() {
  // Fetch data using React Query hooks
  const { data: summary, isLoading: loadingSummary, error: errorSummary } = useDashboardSummary();
  const { data: paymentRate, isLoading: loadingPayment } = usePaymentSuccessRate();
  const { data: alertsData, isLoading: loadingAlerts } = useAlerts({ status: 'new' });
  const { data: forecastData } = useRevenueForecast({
    start_date: subDays(new Date(), 7).toISOString(),
    end_date: addDays(new Date(), 7).toISOString(),
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/50">
      {/* Sticky Header */}
      <header className="sticky top-0 z-50 bg-white/95 border-b shadow-sm">
        <div className="flex h-16 items-center px-8 max-w-[1600px] mx-auto">
          <Button variant="ghost" size="icon" onClick={toggleSidebar}>
            {sidebarOpen ? <X /> : <Menu />}
          </Button>
          <h1 className="flex-1 text-2xl font-bold font-crimson-pro">SME Pulse</h1>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="size-5" />
              {alertsData?.length > 0 && (
                <span className="absolute top-1 right-1 size-2.5 bg-red-500 rounded-full animate-pulse"></span>
              )}
            </Button>
            <Separator orientation="vertical" className="h-6" />
            <UserMenu />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-8 max-w-[1600px] mx-auto">
        {/* Error State */}
        {errorSummary && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="size-4" />
            <AlertDescription>Failed to load dashboard: {errorSummary.message}</AlertDescription>
          </Alert>
        )}

        {/* KPI Metrics Grid - 3 columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {loadingSummary ? (
            // Skeleton loading state
            Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-4 w-24 bg-slate-200 rounded"></div>
                </CardHeader>
                <CardContent>
                  <div className="h-10 w-32 bg-slate-200 rounded"></div>
                </CardContent>
              </Card>
            ))
          ) : (
            // Actual metrics
            [
              { title: 'Doanh thu hôm nay', value: formatCurrency(summary?.daily_revenue), trend: '+2.5%' },
              { title: 'Công nợ khách hàng', value: formatCurrency(summary?.total_ar), trend: '-1.2%' },
              { title: 'Tiền mặt có sẵn', value: formatCurrency(summary?.cash_balance), trend: '+0.8%' },
            ].map((metric) => (
              <Card key={metric.title} className="bg-white hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-600">{metric.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{metric.value}</div>
                  <p className="text-xs text-green-600 mt-2">↑ {metric.trend}</p>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        {/* Charts Grid - 2 columns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Charts */}
          <div className="lg:col-span-2 space-y-6">
            {/* Revenue Chart */}
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>Doanh thu 14 ngày</CardTitle>
              </CardHeader>
              <CardContent className="h-80">
                {loadingSummary ? (
                  <Skeleton className="h-full" />
                ) : (
                  <RevenueChart data={summary?.revenue_history} />
                )}
              </CardContent>
            </Card>

            {/* Forecast Chart */}
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>Dự báo doanh thu 7 ngày (Prophet AI)</CardTitle>
              </CardHeader>
              <CardContent className="h-80">
                {loadingSummary ? (
                  <Skeleton className="h-full" />
                ) : (
                  <ForecastChart 
                    data={forecastData?.predictions}
                    confidence={0.95}
                  />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right: Alerts */}
          <Card className="bg-white h-fit">
            <CardHeader>
              <CardTitle className="text-lg">⚠️ Cảnh báo AI ({alertsData?.length || 0})</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-96 overflow-y-auto">
              {loadingAlerts ? (
                <Spinner />
              ) : alertsData?.length === 0 ? (
                <p className="text-slate-500 text-center py-6">Không có cảnh báo mới</p>
              ) : (
                alertsData.map((alert) => (
                  <div 
                    key={alert.id} 
                    className="p-3 rounded-lg border-l-4 border-red-500 bg-red-50 cursor-pointer hover:bg-red-100 transition"
                  >
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="size-4 text-red-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-slate-900">{alert.title}</p>
                        <p className="text-xs text-slate-600 mt-1">{alert.description}</p>
                        <p className="text-xs text-slate-500 mt-2">{formatDistanceToNow(alert.created_at, { locale: vi })}</p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
```

### 4.5 Forecast Chart with Confidence Intervals

**Đường dẫn:** [frontend/src/components/ForecastChart.tsx](frontend/src/components/ForecastChart.tsx)

```tsx
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export function ForecastChart({ data, confidence = 0.95 }: ForecastChartProps) {
  const { data: forecastData, isLoading } = useRevenueForecast({
    start_date: subDays(new Date(), 7).toISOString().split('T')[0],
    end_date: addDays(new Date(), 7).toISOString().split('T')[0],
  });

  if (isLoading) return <div className="animate-pulse h-80 bg-slate-100 rounded" />;
  if (!forecastData?.data?.length) return <div>Không có dữ liệu</div>;

  // Transform data for chart
  const chartData = forecastData.data.map((point) => ({
    date: format(new Date(point.date), 'dd/MM'),
    actual: point.actual,
    forecast: point.forecast,
    lower: point.lower_bound,
    upper: point.upper_bound,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart 
        data={chartData}
        margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
      >
        <defs>
          {/* Gradient for forecast area */}
          <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
          {/* Gradient for confidence interval */}
          <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#dbeafe" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#dbeafe" stopOpacity={0} />
          </linearGradient>
        </defs>
        
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="date" stroke="#64748b" />
        <YAxis stroke="#64748b" />
        <Tooltip 
          contentStyle={{
            backgroundColor: '#fff',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '12px',
          }}
          formatter={(value) => `₫${(value / 1000000).toFixed(1)}M`}
          labelFormatter={(label) => `Ngày ${label}`}
        />
        <Legend />

        {/* Confidence Interval (shaded area) */}
        <Area 
          type="monotone" 
          dataKey="upper" 
          stroke="none" 
          fill="url(#colorConfidence)" 
          name={`Upper Bound (${(1 + (1-confidence)/2)*100}%)`}
        />
        <Area 
          type="monotone" 
          dataKey="lower" 
          stroke="none" 
          fill="white" 
          name={`Lower Bound (${(confidence/2)*100}%)`}
        />

        {/* Forecast line */}
        <Line 
          type="monotone" 
          dataKey="forecast" 
          stroke="#10b981" 
          strokeWidth={2}
          dot={{ fill: '#10b981', r: 4 }}
          name="Dự báo"
        />

        {/* Actual historical data */}
        <Line 
          type="monotone" 
          dataKey="actual" 
          stroke="#0284c7" 
          strokeWidth={2}
          dot={{ fill: '#0284c7', r: 4 }}
          name="Thực tế"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

### 4.5 Payment Integration (VietQR)

**Đường dẫn:** [frontend/src/components/Payments.tsx](frontend/src/components/Payments.tsx) (line 259-280)

```tsx
// VietQR Code Generation
const generateVietQRUrl = (amount: number, description: string): string => {
  const bankCode = 'MB';           // MB Bank
  const accountNumber = '123456789';
  const template = 'compact2';     // Compact template
  
  // Construct VietQR API URL
  const qrUrl = new URL('https://img.vietqr.io/image');
  qrUrl.pathname += `/${bankCode}-${accountNumber}-${template}.png`;
  qrUrl.searchParams.append('amount', amount.toString());
  qrUrl.searchParams.append('addInfo', description);
  qrUrl.searchParams.append('accountName', 'CONG_TY_ABC');
  
  return qrUrl.toString();
};

export function PaymentModal({ invoiceId, amount, dueDate }: PaymentModalProps) {
  const [paymentMethod, setPaymentMethod] = useState<'transfer' | 'cash' | 'vietqr'>('transfer');
  
  const qrUrl = generateVietQRUrl(
    amount,
    `INV-${invoiceId} HSD: ${format(dueDate, 'dd/MM/yyyy')}`
  );

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Thanh toán hóa đơn #{invoiceId}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Tabs: Transfer, Cash, VietQR */}
          <Tabs value={paymentMethod} onValueChange={setPaymentMethod}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="transfer">💳 Chuyển khoản</TabsTrigger>
              <TabsTrigger value="cash">💰 Tiền mặt</TabsTrigger>
              <TabsTrigger value="vietqr">📱 VietQR</TabsTrigger>
            </TabsList>

            <TabsContent value="vietqr">
              {/* VietQR Code Display */}
              <div className="flex flex-col items-center gap-4 py-6">
                <img 
                  src={qrUrl} 
                  alt="VietQR Code" 
                  className="w-56 h-56 border-2 border-slate-200 rounded-lg p-2"
                />
                <div className="text-center">
                  <p className="text-sm text-slate-600">Quét mã QR để thanh toán</p>
                  <p className="font-semibold text-lg">₫{formatCurrency(amount)}</p>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setIsOpen(false)}>Hủy</Button>
          <Button onClick={handleConfirmPayment}>Xác nhận</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### 4.6 Loading State (Skeleton)

**Đường dẫn:** [frontend/src/components/Dashboard.tsx](frontend/src/components/Dashboard.tsx) (line 100-115)

```tsx
{loadingSummary ? (
  // Loading skeleton for metrics
  Array.from({ length: 3 }).map((_, index) => (
    <Card key={index}>
      <CardHeader>
        <div className="h-4 w-24 bg-slate-200 rounded animate-pulse"></div>
      </CardHeader>
      <CardContent>
        <div className="h-10 w-32 bg-slate-200 rounded animate-pulse"></div>
      </CardContent>
    </Card>
  ))
) : (
  metrics.map((metric) => <MetricCard key={metric.title} {...metric} />)
)}
```

---

## 5. DATA PIPELINE & AUTOMATION

### 5.1 Daily ETL DAG (sme_pulse_daily_etl)

**Đường dẫn:** [airflow/dags/sme_pulse_daily_etl.py](airflow/dags/sme_pulse_daily_etl.py)

**Schedule:** Daily at 2:00 AM VN time (UTC+7)

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup

with DAG(
    'sme_pulse_daily_etl',
    description='Daily ETL: App DB → Bronze → Silver/Gold layers',
    schedule_interval='0 2 * * *',        # 2:00 AM every day
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={
        'retries': 2,
        'retry_delay': timedelta(minutes=5),
        'timeout': timedelta(hours=2),
    }
) as dag:
    
    # Task 1: Verify infrastructure health
    verify_infra = PythonOperator(
        task_id='verify_infrastructure',
        python_callable=verify_infrastructure,  # Checks MinIO, Trino, App DB, Redis
        op_kwargs={'timeout': 60}
    )
    
    # Task 2: Extract from App DB (OLTP) → MinIO Bronze (OLAP)
    extract_app_db = PythonOperator(
        task_id='extract_app_db_to_bronze',
        python_callable=extract_transactional_data,
        op_kwargs={
            'org_id': '{{ dag.params.org_id }}',
            'incremental': True,  # Only extract rows with updated_at >= last_run_timestamp
        }
    )
    
    # Task Group 3: dbt Transformations
    with TaskGroup(name='dbt_transformations') as dbt_group:
        # Step 3.1: Silver Layer - Staging & Feature Engineering
        run_staging = BashOperator(
            task_id='run_staging',
            bash_command='cd /dbt && dbt run --select path:models/silver/stg_* --profiles-dir .',
            env={'DBT_PROFILES_DIR': '/dbt'}
        )
        
        run_features = BashOperator(
            task_id='run_features',
            bash_command='cd /dbt && dbt run --select path:models/silver/features/*',
        )
        
        # Step 3.2: Gold Layer - Facts & Dimensions
        run_gold = BashOperator(
            task_id='run_gold',
            bash_command='cd /dbt && dbt run --select path:models/gold/*',
        )
        
        # Dependency within TaskGroup
        [run_staging >> run_features] >> run_gold
    
    # Task 4: Data Quality Checks
    validate_data = PythonOperator(
        task_id='validate_data_quality',
        python_callable=run_data_quality_checks,
        op_kwargs={
            'tables': [
                'sme_lake.gold.fact_ar_invoices',
                'sme_lake.gold.fact_bank_txn',
                'sme_lake.gold.ml_training_cashflow_fcst',
            ]
        }
    )
    
    # Task 5: Generate daily report
    generate_report = PythonOperator(
        task_id='generate_daily_report',
        python_callable=generate_etl_report,
        op_kwargs={'run_date': '{{ ds }}'}
    )
    
    # DAG dependencies
    verify_infra >> extract_app_db >> dbt_group >> validate_data >> generate_report
```

**Task Details:**

| Task | Purpose | Timeout | Retry |
|------|---------|---------|-------|
| verify_infrastructure | Health check: MinIO, Trino, PostgreSQL | 1m | 2x |
| extract_app_db_to_bronze | CDC from App DB (incremental) | 30m | 2x |
| run_staging | Create silver stg_* tables | 15m | 1x |
| run_features | Engineer silver feature tables | 20m | 1x |
| run_gold | Build gold fact/dim tables | 25m | 1x |
| validate_data_quality | dbt tests + custom checks | 10m | 0x (fail fast) |
| generate_daily_report | Email HTML summary | 5m | 1x |

### 5.2 Weekly ML Training DAG (sme_pulse_ml_training)

**Đường dẫn:** [airflow/dags/sme_pulse_ml_training.py](airflow/dags/sme_pulse_ml_training.py)

**Schedule:** Weekly on Sunday 1:00 AM VN time

```python
with DAG(
    'sme_pulse_ml_training',
    description='Weekly ML Model Retraining: Prophet + Isolation Forest',
    schedule_interval='0 1 * * 0',      # 1:00 AM Sunday
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:
    
    # Task 1: UC09 - Prophet Cashflow Forecast
    train_prophet = PythonOperator(
        task_id='train_prophet_forecast',
        python_callable=train_cashflow_forecast,
        op_kwargs={
            'training_window_days': 90,
            'forecast_horizon_days': 30,
            'model_name': 'prophet_v1',
        }
    )
    
    # Task 2: UC10 - Isolation Forest Anomaly Detection
    train_isolation_forest = PythonOperator(
        task_id='train_isolation_forest',
        python_callable=train_anomaly_detector,
        op_kwargs={
            'training_window_days': 180,
            'contamination_rate': 0.05,  # 5% expected anomalies
            'model_name': 'isolation_forest_v1',
        }
    )
    
    # Task 3: Register models to MLflow
    register_models = PythonOperator(
        task_id='register_models_to_mlflow',
        python_callable=register_production_models,
        op_kwargs={'promote_to_prod': True}
    )
    
    # Task 4: Generate ML report
    ml_report = PythonOperator(
        task_id='generate_ml_report',
        python_callable=generate_ml_metrics_report,
    )
    
    [train_prophet, train_isolation_forest] >> register_models >> ml_report
```

**ML Training Code:**

**UC09 Prophet (Đường dẫn:** [ops/ml/UC09-forecasting/train_cashflow_model.py](ops/ml/UC09-forecasting/train_cashflow_model.py)**

```python
from prophet import Prophet
from sklearn.preprocessing import StandardScaler
import mlflow
import trino.dbapi

def train_cashflow_forecast(training_window_days=90, forecast_horizon_days=30):
    """Train Prophet model for revenue forecasting with VN holidays."""
    
    # Step 1: Fetch training data from silver.ml_training_cashflow_fcst
    conn = trino.dbapi.connect(
        host='trino',
        port=8080,
        user='ml_training',
        catalog='sme_lake',
        schema='silver',
    )
    cursor = conn.cursor()
    
    query = f"""
    SELECT 
        forecast_date as ds,
        total_revenue as y,
        is_weekend,
        is_holiday_vn,
        is_beginning_of_month,
        day_of_month,
        sin_month,
        cos_month
    FROM silver.ml_training_cashflow_fcst
    WHERE forecast_date >= CURRENT_DATE - INTERVAL '{training_window_days}' day
    ORDER BY forecast_date
    """
    
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])
    
    # Step 2: Create Prophet model with seasonality & regressors
    model = Prophet(
        interval_width=0.95,           # 95% confidence interval
        yearly_seasonality=True,       # Account for seasonal variations
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,  # Reduced changepoint flexibility
        seasonality_mode='additive',
    )
    
    # Add regressors (external features)
    for regressor in ['is_weekend', 'is_holiday_vn', 'is_beginning_of_month', 'sin_month', 'cos_month']:
        model.add_regressor(regressor)
    
    # Add Vietnam holidays (Tet, Quoc Khanh, etc.)
    model.add_country_holidays('VN')
    
    # Step 3: Fit the model
    model.fit(df)
    
    # Step 4: Generate future forecast
    future = model.make_future_dataframe(periods=forecast_horizon_days)
    # Attach regressor values for future dates
    future = attach_future_regressors(future)
    
    forecast = model.predict(future)
    
    # Step 5: Log to MLflow
    mlflow.set_experiment('sme_pulse_forecasting')
    with mlflow.start_run(run_name=f'prophet_cashflow_{datetime.now().strftime("%Y%m%d")}'):
        mlflow.log_params({
            'algorithm': 'Prophet',
            'training_window_days': training_window_days,
            'forecast_horizon': forecast_horizon_days,
            'seasonality_mode': 'additive',
        })
        
        # Calculate metrics
        y_true = df['y'].tail(14).values  # Last 2 weeks
        y_pred = model.predict(df[['ds']].tail(14))['yhat'].values
        mape = mean_absolute_percentage_error(y_true, y_pred)
        
        mlflow.log_metric('mape', mape)
        mlflow.log_artifact(f'/tmp/prophet_model', artifact_path='model')
    
    # Step 6: Write forecast to Iceberg table (gold.ml_cashflow_forecast)
    forecast_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    forecast_df.columns = ['forecast_date', 'predicted_cashflow', 'lower_bound', 'upper_bound']
    forecast_df['model_name'] = 'prophet_v1'
    forecast_df['prediction_timestamp'] = datetime.now()
    
    # Write to Trino Iceberg
    write_to_iceberg(forecast_df, 'sme_lake.gold.ml_cashflow_forecast')
```

**UC10 Isolation Forest (Đường dẫn:** [ops/ml/UC10-anomoly_detection/train_isolation_forest.py](ops/ml/UC10-anomoly_detection/train_isolation_forest.py)**

```python
from sklearn.ensemble import IsolationForest
import mlflow

def train_anomaly_detector(training_window_days=180, contamination_rate=0.05):
    """Train Isolation Forest for transaction anomaly detection."""
    
    # Step 1: Fetch training data (last 180 days)
    conn = trino.dbapi.connect(host='trino', port=8080, user='ml_training')
    cursor = conn.cursor()
    
    df = pd.read_sql("""
    SELECT 
        transaction_id,
        customer_id,
        transaction_amount,
        days_since_last_txn,
        avg_transaction_amount_30d,
        transaction_frequency_30d,
        is_weekend,
        is_holiday_vn,
        customer_credit_limit,
        days_past_due
    FROM silver.ml_training_anomaly_detection
    WHERE transaction_date >= CURRENT_DATE - INTERVAL '{training_window_days}' day
    """, conn)
    
    # Step 2: Feature scaling
    scaler = StandardScaler()
    features = ['transaction_amount', 'days_since_last_txn', 'avg_transaction_amount_30d',
                'transaction_frequency_30d', 'customer_credit_limit', 'days_past_due']
    
    X_scaled = scaler.fit_transform(df[features])
    
    # Step 3: Train Isolation Forest
    model = IsolationForest(
        contamination=contamination_rate,  # Expect 5% anomalies
        random_state=42,
        n_estimators=100,
        max_samples='auto',
    )
    
    # Fit and predict
    anomaly_scores = model.fit_predict(X_scaled)  # -1 = anomaly, 1 = normal
    anomaly_proba = model.score_samples(X_scaled)  # Negative = more anomalous
    
    # Step 4: Log to MLflow
    mlflow.set_experiment('sme_pulse_anomaly_detection')
    with mlflow.start_run(run_name=f'isolation_forest_{datetime.now().strftime("%Y%m%d")}'):
        mlflow.log_params({
            'algorithm': 'Isolation Forest',
            'contamination': contamination_rate,
            'n_estimators': 100,
        })
        
        # Metrics
        n_anomalies = (anomaly_scores == -1).sum()
        anomaly_rate = n_anomalies / len(df)
        
        mlflow.log_metric('n_anomalies', n_anomalies)
        mlflow.log_metric('anomaly_rate', anomaly_rate)
    
    # Step 5: Write predictions to Iceberg (gold.ml_ar_anomalies)
    result_df = df[['customer_id', 'transaction_id', 'transaction_amount']].copy()
    result_df['anomaly_score'] = anomaly_proba
    result_df['is_anomaly'] = (anomaly_scores == -1).astype(int)
    result_df['anomaly_severity'] = result_df['anomaly_score'].apply(
        lambda x: 'HIGH' if x < -0.5 else ('MEDIUM' if x < -0.2 else 'LOW')
    )
    
    write_to_iceberg(result_df, 'sme_lake.gold.ml_ar_anomalies')
```

    write_to_iceberg(result_df, 'sme_lake.gold.ml_ar_anomalies')
```

### 5.3 Data Flow & Medallion Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                          DATA PIPELINE FLOW                         │
└───────────────────────────────────────────────────────────────────┘

STEP 1: EXTRACTION (App DB → MinIO Bronze)
┌──────────────────────────────────────────────────────────────┐
│ Source:                                                      │
│ - PostgreSQL 5433 (App DB OLTP)                             │
│ - Tables: User, Organization, ARInvoice, APBill, Payment... │
│                                                              │
│ Method: Change Data Capture (CDC) via updated_at            │
│ Frequency: Daily 2:00 AM                                    │
│ Format: Parquet files in MinIO/sme_lake/bronze/             │
└──────────────────────────────────────────────────────────────┘
                            ↓
STEP 2: TRANSFORMATION (Trino External Tables → dbt)
┌──────────────────────────────────────────────────────────────┐
│ Bronze Layer (MinIO):                                         │
│ - External tables in Trino (sme_lake.bronze.*)              │
│ - Schema: _scd_type=1 (incremental snapshots)               │
│                                                              │
│ Silver Layer (dbt staging):                                  │
│ - Staging: stg_ar_invoices, stg_payments, stg_bank_txn     │
│ - Features: ftr_customer_metrics, ftr_temporal_features    │
│ - ML Prep: ml_training_cashflow_fcst, ml_training_anomaly  │
│                                                              │
│ Gold Layer (dbt marts):                                      │
│ - Facts: fact_ar_invoices, fact_payments, fact_bank_txn    │
│ - Dimensions: dim_customer, dim_supplier, dim_account       │
│ - Scores: ml_ar_priority_scores, ml_ar_anomalies           │
└──────────────────────────────────────────────────────────────┘
                            ↓
STEP 3: ML PREDICTIONS (Iceberg Gold → FastAPI)
┌──────────────────────────────────────────────────────────────┐
│ UC09 - Prophet Forecast:                                     │
│ - Input: gold.ml_training_cashflow_fcst                     │
│ - Output: gold.ml_cashflow_forecast (30-day forecast)      │
│ - Columns: forecast_date, predicted_revenue, bounds        │
│                                                              │
│ UC10 - Anomaly Detection:                                    │
│ - Input: gold.ml_training_anomaly_detection                │
│ - Output: gold.ml_ar_anomalies (anomaly scores)            │
│ - Columns: transaction_id, is_anomaly, severity            │
└──────────────────────────────────────────────────────────────┘
                            ↓
STEP 4: SERVING (Iceberg Gold → FastAPI API → React)
┌──────────────────────────────────────────────────────────────┐
│ FastAPI Analytics Module queries:                            │
│ SELECT * FROM sme_lake.gold.ml_cashflow_forecast            │
│ SELECT * FROM sme_lake.gold.ml_ar_anomalies                 │
│                                                              │
│ React Dashboard fetches via REST API:                        │
│ GET /api/v1/analytics/forecast/revenue                      │
│ GET /api/v1/analytics/anomalies/revenue                     │
└──────────────────────────────────────────────────────────────┘
```

**dbt Models Structure:**

**Đường dẫn:** [dbt/models/](dbt/models/)

```
dbt/models/
├── silver/
│   ├── stg_app_ar_invoices.sql          # Select * from bronze.ar_invoices
│   ├── stg_app_ap_bills.sql             # Select * from bronze.ap_bills
│   ├── stg_bank_txn_vn.sql              # Select * from bronze.bank_transactions
│   ├── stg_payments.sql                 # Dedup + soft delete handling
│   ├── features/
│   │   ├── ftr_customer_metrics.sql     # DSO, payment history, credit metrics
│   │   ├── ftr_temporal_features.sql    # is_weekend, is_holiday, sin/cos month
│   │   └── ftr_transaction_features.sql # Rolling averages, frequency
│   └── ml_training/
│       ├── ml_training_cashflow_fcst.sql     # 90-day cashflow history for Prophet
│       └── ml_training_anomaly_detection.sql # 180-day transaction features
├── gold/
│   ├── facts/
│   │   ├── fact_ar_invoices.sql         # Dim: customer, account, date
│   │   ├── fact_ap_bills.sql            # Dim: supplier, account, date
│   │   ├── fact_payments.sql            # Fact: amount, method, date
│   │   └── fact_bank_txn.sql            # Fact: amount, type, bank
│   ├── dimensions/
│   │   ├── dim_customer.sql             # Customer SCD Type 2
│   │   ├── dim_supplier.sql             # Supplier attributes
│   │   └── dim_account.sql              # Account & routing info
│   └── ml_scores/
│       ├── ml_cashflow_forecast.sql     # Refreshed weekly by Prophet
│       ├── ml_ar_anomalies.sql          # Refreshed weekly by Isolation Forest
│       └── ml_ar_priority_scores.sql    # Heuristic: DSO + days_past_due
```

### 5.4 dbt SQL Example

**Đường dẫn:** [dbt/models/gold/facts/fact_ar_invoices.sql](dbt/models/gold/facts/fact_ar_invoices.sql)

```sql
{{ config(
    materialized='table',
    schema='gold',
    tags=['daily', 'core']
) }}

WITH staging AS (
    SELECT 
        id as invoice_id,
        organization_id,
        customer_id,
        invoice_date,
        due_date,
        amount,
        paid_amount,
        status,
        updated_at
    FROM {{ ref('stg_app_ar_invoices') }}
    WHERE status IN ('issued', 'overdue', 'paid')
),

customer_features AS (
    SELECT 
        customer_id,
        avg_invoice_amount,
        days_sales_outstanding,
        invoice_count_30d,
        last_payment_date
    FROM {{ ref('ftr_customer_metrics') }}
),

temporal_features AS (
    SELECT 
        DATE(invoice_date) as date_key,
        is_weekend,
        is_holiday_vn,
        month,
        sin_month,
        cos_month
    FROM {{ ref('ftr_temporal_features') }}
)

SELECT 
    staging.invoice_id,
    staging.organization_id,
    staging.customer_id,
    customer_features.days_sales_outstanding as dso,
    DATEDIFF(CURRENT_DATE, staging.due_date) as days_overdue,
    staging.amount,
    staging.paid_amount,
    staging.amount - staging.paid_amount as outstanding_amount,
    staging.status,
    temporal_features.is_holiday_vn,
    staging.invoice_date,
    staging.due_date,
    CURRENT_TIMESTAMP as load_timestamp

FROM staging
LEFT JOIN customer_features USING (customer_id)
LEFT JOIN temporal_features ON DATE(staging.invoice_date) = temporal_features.date_key

WHERE staging.updated_at >= DATEADD(day, -1, CURRENT_DATE)
```

---

## 6. CƠSỞ DỮ LIỆU & CẤU TRÚC SCHEMA

### 6.0 Sơ đồ Thực thể - Liên kết (Operational ERD - OLTP)

```plantuml
@startuml
entity ORGANIZATION {
  *id : int <<PK>>
  *name : string <<UK>>
  country : string
  status : string
  subscription_tier : string
  created_at : timestamp
}

entity USER {
  *id : int <<PK>>
  *org_id : int <<FK>>
  *email : string <<UK>>
  password_hash : string
  full_name : string
  status : string
  created_at : timestamp
}

entity ROLE {
  *id : int <<PK>>
  *code : string <<UK>>
  name : string
  permissions : json
}

entity USER_ROLE {
  *id : int <<PK>>
  *user_id : int <<FK>>
  *role_id : int <<FK>>
}

entity CUSTOMER {
  *id : int <<PK>>
  *org_id : int <<FK>>
  name : string
  email : string
  phone : string
  address : string
  tax_code : string
  credit_limit : decimal
  status : string
  created_at : timestamp
}

entity SUPPLIER {
  *id : int <<PK>>
  *org_id : int <<FK>>
  name : string
  email : string
  phone : string
  address : string
  created_at : timestamp
}

entity ACCOUNT {
  *id : int <<PK>>
  *org_id : int <<FK>>
  code : string
  name : string
  category : string
  balance : decimal
  currency : string
  created_at : timestamp
}

entity AR_INVOICE {
  *id : int <<PK>>
  *org_id : int <<FK>>
  *customer_id : int <<FK>>
  *invoice_number : string <<UK>>
  invoice_date : date
  due_date : date
  amount : decimal
  paid_amount : decimal
  status : string
  notes : text
  created_at : timestamp
  updated_at : timestamp <<CDC>>
}

entity AP_BILL {
  *id : int <<PK>>
  *org_id : int <<FK>>
  *supplier_id : int <<FK>>
  *bill_number : string <<UK>>
  bill_date : date
  due_date : date
  amount : decimal
  paid_amount : decimal
  status : string
  created_at : timestamp
  updated_at : timestamp
}

entity PAYMENT {
  *id : int <<PK>>
  *org_id : int <<FK>>
  invoice_id : int <<FK>>
  bill_id : int <<FK>>
  amount : decimal
  payment_date : date
  method : string
  reference_number : string
  status : string
  created_at : timestamp
}

entity PAYMENT_ALLOCATION {
  *id : int <<PK>>
  *payment_id : int <<FK>>
  invoice_id : int <<FK>>
  bill_id : int <<FK>>
  allocated_amount : decimal
  created_at : timestamp
}

ORGANIZATION ||--o{ USER : has
ORGANIZATION ||--o{ CUSTOMER : has
ORGANIZATION ||--o{ SUPPLIER : has
ORGANIZATION ||--o{ ACCOUNT : has
ORGANIZATION ||--o{ AR_INVOICE : has
ORGANIZATION ||--o{ AP_BILL : has
ORGANIZATION ||--o{ PAYMENT : has

USER }o--|| ORGANIZATION : belongs_to
USER }o--o{ ROLE : assigned_via

ROLE ||--o{ USER_ROLE : contains
USER ||--o{ USER_ROLE : contains

CUSTOMER ||--o{ AR_INVOICE : issues
SUPPLIER ||--o{ AP_BILL : sends

AR_INVOICE ||--o{ PAYMENT : receives
AR_INVOICE ||--o{ PAYMENT_ALLOCATION : allocated_by

AP_BILL ||--o{ PAYMENT : receives
AP_BILL ||--o{ PAYMENT_ALLOCATION : allocated_by

PAYMENT ||--o{ PAYMENT_ALLOCATION : allocates_to
PAYMENT_ALLOCATION }o--|| AR_INVOICE : allocates_to
PAYMENT_ALLOCATION }o--|| AP_BILL : allocates_to

@enduml
```

**Giải thích mối quan hệ:**

| Quan hệ | Loại | Mô tả |
|---------|------|-------|
| Organization → User | 1:N | Một org có nhiều user |
| Organization → Customer | 1:N | Một org có nhiều khách hàng |
| Organization → Supplier | 1:N | Một org có nhiều nhà cung cấp |
| Organization → Account | 1:N | Một org có nhiều tài khoản kế toán |
| Organization → AR Invoice | 1:N | Một org phát hành nhiều hóa đơn bán |
| Organization → AP Bill | 1:N | Một org nhận nhiều hóa đơn mua |
| Organization → Payment | 1:N | Một org có nhiều giao dịch thanh toán |
| User ↔ Role | M:N | Một user có nhiều role (qua bảng trung gian) |
| Customer → AR Invoice | 1:N | Một khách hàng nhận nhiều hóa đơn |
| Supplier → AP Bill | 1:N | Một nhà cung cấp gửi nhiều hóa đơn |
| AR Invoice ↔ Payment | M:N | Một hóa đơn bán được thanh toán qua nhiều lần (qua PaymentAllocation) |
| AP Bill ↔ Payment | M:N | Một hóa đơn mua được thanh toán qua nhiều lần (qua PaymentAllocation) |

**Key Design Patterns:**

1. **Multi-tenancy:** Mọi bảng chính (User, Customer, AR_Invoice, etc.) đều có `org_id` để isolation
2. **CDC (Change Data Capture):** `AR_INVOICE.updated_at` dùng cho incremental extraction
3. **Many-to-Many Payment:** `PAYMENT_ALLOCATION` cho phép 1 thanh toán có thể allocate cho nhiều hóa đơn
4. **Unique Constraints:** invoice_number, bill_number, email (unique per org)
5. **Nullable FK:** Payment có thể liên kết tới invoice_id hoặc bill_id (hoặc cả hai)

### 6.1 PostgreSQL OLTP Schema (App Database)

**Đường dẫn:** [backend/app/models/core.py](backend/app/models/core.py), [backend/app/models/finance.py](backend/app/models/finance.py)

**Port:** 5433

```python
# Core Tables (backend/app/models/core.py)

class Organization(Base):
    """Multi-tenancy root"""
    __tablename__ = "organization"
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(255), unique=True)
    country: str = Column(String(2))  # VN
    status: str = Column(String(20))  # active, inactive
    subscription_tier: str = Column(String(50))  # free, pro, enterprise
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

class User(Base):
    """Employee/user accounts"""
    __tablename__ = "user"
    id: int = Column(Integer, primary_key=True)
    org_id: int = Column(Integer, ForeignKey("organization.id"))
    email: str = Column(String(255), unique=True, index=True)
    password_hash: str = Column(String(255))
    full_name: str = Column(String(255))
    status: str = Column(String(20))  # active, disabled, invited
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # RBAC
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

class Role(Base):
    """RBAC roles"""
    __tablename__ = "role"
    id: int = Column(Integer, primary_key=True)
    code: str = Column(String(50), unique=True)  # owner, accountant, cashier, admin
    name: str = Column(String(255))
    permissions: list = Column(JSON)  # {"read_reports", "create_invoice", ...}

class UserRole(Base):
    """User-Role assignment (many-to-many)"""
    __tablename__ = "user_role"
    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("user.id"))
    role_id: int = Column(Integer, ForeignKey("role.id"))
    
    user = relationship("User", back_populates="roles")
    role = relationship("Role")

class Customer(Base):
    """Customer/buyer"""
    __tablename__ = "customer"
    id: int = Column(Integer, primary_key=True)
    org_id: int = Column(Integer, ForeignKey("organization.id"), index=True)
    name: str = Column(String(255))
    email: str = Column(String(255))
    phone: str = Column(String(20))
    address: str = Column(String(500))
    tax_code: str = Column(String(20))
    credit_limit: Decimal = Column(Numeric(15, 2))
    status: str = Column(String(20))  # active, inactive
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

class Account(Base):
    """Accounting account (chart of accounts)"""
    __tablename__ = "account"
    id: int = Column(Integer, primary_key=True)
    org_id: int = Column(Integer, ForeignKey("organization.id"))
    code: str = Column(String(20))  # 1101, 1102, 2101, etc.
    name: str = Column(String(255))
    category: str = Column(String(20))  # asset, liability, revenue, expense
    balance: Decimal = Column(Numeric(15, 2), default=0)
    currency: str = Column(String(3), default='VND')

# Finance Tables (backend/app/models/finance.py)

class ARInvoice(Base):
    """Account Receivable - Sales Invoice"""
    __tablename__ = "ar_invoice"
    id: int = Column(Integer, primary_key=True)
    org_id: int = Column(Integer, ForeignKey("organization.id"), index=True)
    customer_id: int = Column(Integer, ForeignKey("customer.id"))
    invoice_number: str = Column(String(50), unique=True)
    invoice_date: date = Column(Date)
    due_date: date = Column(Date)
    amount: Decimal = Column(Numeric(15, 2))
    paid_amount: Decimal = Column(Numeric(15, 2), default=0)
    status: str = Column(String(20))  # issued, partially_paid, paid, overdue, cancelled
    notes: str = Column(Text)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    customer = relationship("Customer")

class APBill(Base):
    """Account Payable - Supplier Invoice"""
    __tablename__ = "ap_bill"
    id: int = Column(Integer, primary_key=True)
    org_id: int = Column(Integer, ForeignKey("organization.id"), index=True)
    supplier_id: int = Column(Integer, ForeignKey("supplier.id"))
    bill_number: str = Column(String(50), unique=True)
    bill_date: date = Column(Date)
    due_date: date = Column(Date)
    amount: Decimal = Column(Numeric(15, 2))
    paid_amount: Decimal = Column(Numeric(15, 2), default=0)
    status: str = Column(String(20))  # issued, partially_paid, paid, overdue
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Payment(Base):
    """Payment transaction"""
    __tablename__ = "payment"
    id: int = Column(Integer, primary_key=True)
    org_id: int = Column(Integer, ForeignKey("organization.id"), index=True)
    invoice_id: int = Column(Integer, ForeignKey("ar_invoice.id"), nullable=True)
    bill_id: int = Column(Integer, ForeignKey("ap_bill.id"), nullable=True)
    amount: Decimal = Column(Numeric(15, 2))
    payment_date: date = Column(Date)
    method: str = Column(String(20))  # transfer, cash, card, vietqr
    reference_number: str = Column(String(100))
    status: str = Column(String(20))  # pending, success, failed
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

class PaymentAllocation(Base):
    """How a payment is allocated to invoices"""
    __tablename__ = "payment_allocation"
    id: int = Column(Integer, primary_key=True)
    payment_id: int = Column(Integer, ForeignKey("payment.id"), cascade="delete")
    invoice_id: int = Column(Integer, ForeignKey("ar_invoice.id"))
    allocated_amount: Decimal = Column(Numeric(15, 2))
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

**Key Indexes:**
```sql
CREATE INDEX idx_ar_invoice_org_status ON ar_invoice(org_id, status);
CREATE INDEX idx_ar_invoice_due_date ON ar_invoice(due_date);
CREATE INDEX idx_ar_invoice_customer ON ar_invoice(customer_id);
CREATE INDEX idx_ar_invoice_updated_at ON ar_invoice(updated_at);  -- For CDC

CREATE INDEX idx_payment_org_date ON payment(org_id, payment_date);
CREATE INDEX idx_payment_invoice ON payment(invoice_id);
```

### 6.2 Trino + Iceberg (OLAP Lakehouse)

**Port:** 8080

**Catalogs:**
- `sme_lake` = MinIO backend
- `memory` = Ad-hoc queries

**Schemas:**
```
sme_lake.bronze      # External tables pointing to MinIO Parquet
sme_lake.silver      # dbt staging & feature tables
sme_lake.gold        # dbt fact & dimension tables + ML outputs
```

**Example Iceberg Table:**
```sql
-- Create Iceberg table for predictions
CREATE TABLE sme_lake.gold.ml_cashflow_forecast (
    forecast_date DATE,
    predicted_cashflow DECIMAL(15, 2),
    lower_bound DECIMAL(15, 2),
    upper_bound DECIMAL(15, 2),
    model_name VARCHAR(100),
    prediction_timestamp TIMESTAMP
)
WITH (
    format = 'PARQUET',
    partitioning = ARRAY['YEAR(forecast_date)'],  -- Partition by year
    bucketing_version = 2,
    bucket_count = 10
)
USING iceberg;
```

### 6.3 Multi-Tenancy Isolation

**Database Level:**
- Every table has `org_id` column (NOT NULL)
- All queries filtered by `WHERE org_id = current_org_id`

**Application Level:**
```python
# middleware/tenant.py
@app.middleware("http")
async def add_tenant_context(request: Request, call_next):
    # Extract org_id from JWT token
    token = get_token_from_request(request)
    org_id = decode_token(token).get("org_id")
    
    # Set context for all database queries
    request.state.org_id = org_id
    
    return await call_next(request)

# In service layer
async def get_ar_invoices(db: AsyncSession, org_id: int):
    stmt = select(ARInvoice).where(
        ARInvoice.org_id == org_id  # Mandatory tenant filter
    )
    return await db.execute(stmt)
```

---

## 7. BẢO MẬT & AUTHENTICATION

### 7.1 JWT + RBAC Flow

```
LOGIN REQUEST
    ↓
POST /auth/login { email, password }
    ↓ [backend/app/modules/auth/router.py]
authenticate_user() {
    1. Query User by email
    2. Verify bcrypt password hash
    3. Load user.roles
    4. Return (user, roles) or None
}
    ↓ [backend/app/core/security.py]
create_access_token({
    "sub": user_id,
    "org_id": user.org_id,
    "roles": ["owner", "accountant"],
    "exp": datetime.now() + 30 min
}) → signed JWT token
    ↓
RESPONSE: {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "user": { "id": 1, "email": "...", "full_name": "..." },
    "roles": ["owner", "accountant"]
}
    ↓ [Frontend - Login.tsx]
localStorage.setItem('token', access_token)
localStorage.setItem('user', user)
redirect('/dashboard')

AUTHENTICATED REQUEST
    ↓ [Frontend - client.ts]
GET /api/v1/analytics/summary
Header: Authorization: Bearer {token_from_localStorage}
    ↓ [Axios interceptor]
apiClient.interceptors.request.use(config => {
    config.headers.Authorization = `Bearer ${token}`
    return config
})
    ↓ [Backend - FastAPI]
@app.get("/api/v1/analytics/summary", dependencies=[Depends(get_current_user)])
async def get_summary(current_user = Depends(get_current_user)):
    # JWT validation + org_id check + RBAC
    
    ↓ [decode_access_token - core/security.py]
    jwt.decode(token, SECRET_KEY)  # Verify signature + exp
    
    ↓ [get_current_user - modules/auth/dependencies.py]
    user = await db.get(User, payload["sub"])
    assert user.org_id == payload["org_id"]  # Tenant check
    
    ↓ [View business logic]
    return await analytics_service.get_summary(user.org_id)
```

**Đường dẫn:** [backend/app/core/security.py](backend/app/core/security.py)

```python
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> tuple[str, int]:
    """Create JWT token valid for 30 minutes"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.BACKEND_SECRET_KEY,
        algorithm=settings.BACKEND_ALGORITHM
    )
    
    expires_in = int(expires_delta.total_seconds()) if expires_delta else 1800
    
    return encoded_jwt, expires_in

def decode_access_token(token: str) -> Optional[dict]:
    """Verify JWT signature and return claims"""
    try:
        payload = jwt.decode(
            token,
            settings.BACKEND_SECRET_KEY,
            algorithms=[settings.BACKEND_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.JWTError:
        return None  # Invalid token
```

### 7.2 Role-Based Access Control

**Đường dẫn:** [backend/app/modules/auth/dependencies.py](backend/app/modules/auth/dependencies.py)

```python
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scopes={"read": "Read access", "write": "Write access"}
)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validate JWT token and return current user.
    Ensures org_id in token matches user.org_id (multi-tenancy check).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    
    if user_id is None or org_id is None:
        raise credentials_exception
    
    # Fetch user from database
    stmt = select(User).options(
        selectinload(User.roles)
    ).where(User.id == user_id)
    
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Multi-tenancy check: User's org_id must match token's org_id
    if user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization mismatch"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user

def requires_roles(allowed_roles: List[str]):
    """
    Decorator to enforce role-based access control.
    Usage: @app.get("/admin", dependencies=[Depends(requires_roles(["owner", "admin"]))])
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        # Get user roles
        user_roles = [ur.role.code for ur in current_user.roles]
        
        # Check if user has any of the allowed roles
        if not any(role in allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        return current_user
    
    return role_checker

# Usage in routers:
@router.get("/admin/users", dependencies=[Depends(requires_roles(["owner", "admin"]))])
async def list_all_users(current_user: User = Depends(get_current_user)):
    # Only owner/admin can access
    return await user_service.list_users(current_user.org_id)

@router.post("/invoices", dependencies=[Depends(requires_roles(["owner", "accountant"]))])
async def create_invoice(invoice: InvoiceCreate, current_user: User = Depends(get_current_user)):
    # owner/accountant can create invoices
    return await finance_service.create_invoice(current_user.org_id, invoice)
```

### 7.3 Rate Limiting & Security Headers

**Đường dẫn:** [backend/app/middleware/security.py](backend/app/middleware/security.py)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
import secrets

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit API endpoints (5 requests per 60 seconds on /auth/login)"""
    
    def __init__(self, app):
        super().__init__(app)
        self.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["100 per hour"]
        )
        # Special limit for login endpoint
        self.login_limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["5 per 60 seconds"]
        )
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/auth/login" and request.method == "POST":
            # Enforce strict rate limit on login
            try:
                self.login_limiter(request)
            except Exception:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many login attempts"}
                )
        
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
        )
        
        # CORS
        response.headers["Access-Control-Allow-Origin"] = os.getenv("FRONTEND_URL", "http://localhost:5173")
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
```

### 7.4 VietQR Payment Integration

**Đường dẫn:** [frontend/src/components/PaymentModal.tsx](frontend/src/components/PaymentModal.tsx)

```tsx
interface VietQRConfig {
  bankCode: string;         // Bank code (MB, ACB, VCB, etc.)
  accountNumber: string;    // Account number
  accountName: string;      // Account holder name (ASCII)
  templateCode: string;     // 'compact' or 'compact2'
}

function generateVietQRUrl(
  amount: number,
  description: string,
  config: VietQRConfig
): string {
  /**
   * VietQR API endpoint: https://img.vietqr.io/image/{bankCode}-{accountNumber}-{template}.png
   * 
   * Query parameters:
   * - amount: Transaction amount (VND)
   * - addInfo: Bill details / invoice number
   * - accountName: Receiver name (ASCII only)
   */
  
  const baseUrl = 'https://img.vietqr.io/image';
  const path = `/${config.bankCode}-${config.accountNumber}-${config.templateCode}.png`;
  
  const qrUrl = new URL(baseUrl + path);
  qrUrl.searchParams.append('amount', amount.toString());
  qrUrl.searchParams.append('addInfo', description);
  qrUrl.searchParams.append('accountName', config.accountName);
  
  return qrUrl.toString();
}

export function PaymentModal({ invoiceId, amount, customerName }: PaymentModalProps) {
  const [paymentMethod, setPaymentMethod] = useState<'transfer' | 'cash' | 'vietqr'>('transfer');
  
  const vietqrConfig: VietQRConfig = {
    bankCode: 'MB',              // MB Bank
    accountNumber: '0123456789',
    accountName: 'SME_PULSE_CO',
    templateCode: 'compact2'
  };
  
  const qrUrl = generateVietQRUrl(
    amount,
    `INV-${invoiceId}`,
    vietqrConfig
  );
  
  return (
    <Dialog>
      <DialogContent>
        <Tabs value={paymentMethod} onValueChange={setPaymentMethod}>
          <TabsContent value="vietqr">
            <div className="flex flex-col items-center gap-4">
              <img 
                src={qrUrl} 
                alt="VietQR Payment Code"
                className="w-56 h-56 border-2 border-gray-200 p-2"
              />
              <div className="text-center">
                <p className="text-sm text-gray-600">Quét mã QR để thanh toán</p>
                <p className="text-2xl font-bold">₫{amount.toLocaleString('vi-VN')}</p>
                <p className="text-xs text-gray-500 mt-2">Mô tả: INV-{invoiceId}</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

// Payment methods supported:
// 1. VietQR (QR banking)
// 2. Transfer (Bank transfer with reference)
// 3. Cash (Manual entry)
// 4. Card (Credit/debit card)
```

---

## 8. TECH STACK & DEPLOYMENT

### 8.1 Complete Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Frontend** | React | 18.x | UI framework |
| | TypeScript | 5.x | Type safety |
| | Vite | 5.x | Build tool |
| | TailwindCSS | 3.x | Styling |
| | Shadcn/ui | Latest | Component library |
| | @tanstack/react-query | 5.x | Data fetching |
| | Recharts | 2.x | Charting |
| | Axios | 1.x | HTTP client |
| | Framer Motion | 10.x | Animations |
| **Backend** | FastAPI | 0.104.x | Web framework |
| | SQLAlchemy | 2.x | ORM (async) |
| | Pydantic | 2.x | Data validation |
| | Alembic | 1.x | Database migrations |
| | Celery | 5.x | Task queue |
| | Passlib | 1.x | Password hashing |
| | python-jose | 3.x | JWT tokens |
| | Trino DBAPI | Latest | OLAP queries |
| **Database** | PostgreSQL | 15 | OLTP (App data) |
| | Trino | 426+ | Query engine |
| | MinIO | Latest | S3-compatible storage |
| | Apache Iceberg | 1.x | Table format |
| **Data** | dbt | 1.7.x | Transformations |
| | Parquet | Format | File format |
| **ML/AI** | Prophet | 1.1.x | Time series forecasting |
| | Scikit-learn | 1.3.x | Anomaly detection |
| | MLflow | 2.x | Model registry |
| **Orchestration** | Apache Airflow | 2.9.x | Workflow orchestration |
| | LocalExecutor | - | Single-machine execution |
| **Caching/Queue** | Redis | 7.x | Cache + Celery broker |
| **BI** | Metabase | Latest | Dashboards (embedded) |
| **Infrastructure** | Docker | Latest | Containerization |
| | Docker Compose | Latest | Multi-container setup |

### 8.2 Deployment Architecture (docker-compose.yml)

**Đường dẫn:** [docker-compose.yml](docker-compose.yml)

```yaml
version: '3.8'

services:
  # ============ CORE DATABASES ============
  postgres_oltp:
    image: postgres:15-alpine
    ports:
      - "5433:5432"  # App DB (OLTP)
    environment:
      POSTGRES_DB: sme_pulse
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_oltp_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - sme_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres_olap:
    image: postgres:15-alpine
    ports:
      - "5432:5432"  # Data Lake (OLAP backup)
    environment:
      POSTGRES_DB: sme_lake
      POSTGRES_USER: lakehouse_user
    volumes:
      - postgres_olap_data:/var/lib/postgresql/data
    networks:
      - sme_network

  # ============ DATA LAKE ============
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"      # API
      - "9001:9001"      # UI Console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    networks:
      - sme_network

  # ============ QUERY ENGINE ============
  trino:
    image: trinodb/trino:latest
    ports:
      - "8080:8080"
    volumes:
      - ./infra/trino/catalog:/etc/trino/catalog
      - ./hive-metastore/core-site.xml:/etc/trino/core-site.xml
    depends_on:
      - minio
    networks:
      - sme_network

  # ============ ORCHESTRATION ============
  airflow_webserver:
    image: apache/airflow:2.9.3-python3.11
    command: webserver
    ports:
      - "8081:8080"
    environment:
      AIRFLOW_HOME: /home/airflow
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres_oltp:5432/airflow
      AIRFLOW__CORE__DAGS_FOLDER: /home/airflow/dags
      AIRFLOW__SCHEDULER__LOAD_EXAMPLES: 'false'
    volumes:
      - ./airflow/dags:/home/airflow/dags
      - ./airflow/logs:/home/airflow/logs
      - ./airflow/plugins:/home/airflow/plugins
    depends_on:
      - postgres_oltp
    networks:
      - sme_network

  airflow_scheduler:
    image: apache/airflow:2.9.3-python3.11
    command: scheduler
    environment:
      AIRFLOW_HOME: /home/airflow
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres_oltp:5432/airflow
    volumes:
      - ./airflow/dags:/home/airflow/dags
      - ./airflow/logs:/home/airflow/logs
    depends_on:
      - postgres_oltp
      - airflow_webserver
    networks:
      - sme_network

  # ============ BACKEND ============
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://app_user:secure_password@postgres_oltp:5432/sme_pulse
      TRINO_HOST: trino
      TRINO_PORT: 8080
      REDIS_URL: redis://redis:6379
      JWT_SECRET: your_secret_key_here
    depends_on:
      - postgres_oltp
      - trino
      - redis
    volumes:
      - ./backend:/app
    networks:
      - sme_network
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # ============ FRONTEND ============
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      VITE_API_BASE_URL: http://backend:8000
    depends_on:
      - backend
    volumes:
      - ./frontend/src:/app/src
    networks:
      - sme_network
    command: npm run dev

  # ============ CACHING & JOBS ============
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - sme_network

  # ============ BI TOOL ============
  metabase:
    image: metabase/metabase:latest
    ports:
      - "3000:3000"
    environment:
      MB_DB_TYPE: postgres
      MB_DB_DBNAME: metabase
      MB_DB_HOST: postgres_oltp
      MB_DB_USER: metabase_user
      MB_DB_PASS: metabase_pass
    depends_on:
      - postgres_oltp
    networks:
      - sme_network

networks:
  sme_network:
    driver: bridge

volumes:
  postgres_oltp_data:
  postgres_olap_data:
  minio_data:
```

### 8.3 Docker Image Build

**Đường dẫn:** [backend/Dockerfile](backend/Dockerfile)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

# Database migrations
RUN alembic upgrade head

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Đường dẫn:** [frontend/Dockerfile](frontend/Dockerfile)

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build
RUN npm run build

# Serve (dev mode for development)
EXPOSE 5173

CMD ["npm", "run", "dev"]
```

### 8.4 Running the Stack

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down

# Access points:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - Airflow: http://localhost:8081
# - Trino: http://localhost:8080
# - MinIO: http://localhost:9001
# - Redis: localhost:6379
# - Metabase: http://localhost:3000
```

---

## 9. TÓM TẮT & KẾT LUẬN

### 9.1 Key Architecture Decisions

1. **Separate OLTP/OLAP Databases:** App DB (PostgreSQL 5433) handles real-time transactions; Lakehouse (Trino + MinIO) handles analytics & ML

2. **Medallion Architecture:** Bronze (raw Parquet) → Silver (staged) → Gold (facts/dims) ensures data quality progression

3. **JWT + RBAC:** Stateless authentication with role-based access control enables multi-tenancy isolation

4. **Prophet + Isolation Forest:** Facebook Prophet for time-series forecasting (UC09), Scikit-learn Isolation Forest for anomaly detection (UC10)

5. **Async FastAPI:** Non-blocking database queries & background tasks via Celery improve API throughput

6. **React Query Caching:** Reduces API load with intelligent cache invalidation based on stale time

7. **dbt Transformations:** Version-controlled SQL models enable reproducible data pipelines & testing

8. **Airflow Orchestration:** Declarative DAGs with task dependencies ensure reliable, scheduled data processing

### 9.2 File Structure Summary

```
SME_Pulse_Project/
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── main.py             # FastAPI app initialization
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── modules/            # Clean architecture modules
│   │   ├── core/               # Security, config, database
│   │   └── middleware/         # JWT, security headers, rate limiting
│   ├── alembic/                # Database migrations
│   └── requirements.txt         # Python dependencies
├── frontend/                    # React application
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Page-level components
│   │   ├── lib/api/            # API client & React Query hooks
│   │   └── App.tsx             # Main app entry
│   ├── vite.config.ts          # Vite build config
│   └── package.json            # NPM dependencies
├── airflow/                     # Apache Airflow DAGs
│   ├── dags/
│   │   ├── sme_pulse_daily_etl.py        # Daily pipeline
│   │   └── sme_pulse_ml_training.py      # Weekly ML training
│   └── plugins/                # Custom Airflow plugins
├── dbt/                         # Data transformation
│   ├── models/
│   │   ├── silver/             # Staging & features
│   │   └── gold/               # Facts, dims, scores
│   └── dbt_project.yml         # dbt configuration
├── ops/                         # Operations & ML
│   ├── ml/                      # Training scripts
│   │   ├── UC09-forecasting/   # Prophet training
│   │   └── UC10-anomoly_detection/  # Isolation Forest
│   └── external_sources/       # Data ingestion scripts
├── sql/                         # SQL scripts
│   ├── 00_bootstrap_schemas.sql
│   └── ...
├── docker-compose.yml          # Multi-container setup
└── README.md                    # Project documentation
```

### 9.3 Performance Metrics

| Metric | Target | Implementation |
|--------|--------|-----------------|
| API Response Time (p95) | <200ms | FastAPI + async queries |
| Daily ETL Duration | <1 hour | Optimized dbt + parallel tasks |
| Forecast Accuracy (MAPE) | <10% | Prophet with VN holidays + seasonality |
| Anomaly Detection (Precision) | >85% | Isolation Forest with feature engineering |
| Dashboard Load Time | <2s | React Query caching |
| Login Attempt Rate Limit | 5/60s | RateLimitMiddleware |

### 9.4 Future Enhancements

- [ ] GraphQL API for frontend flexibility
- [ ] Real-time streaming with Kafka
- [ ] Advanced ML: XGBoost for demand forecasting
- [ ] Mobile app (React Native)
- [ ] Multi-language support (i18n)
- [ ] Advanced RBAC with permission granularity
- [ ] Audit logging for compliance
- [ ] Elasticsearch for full-text search

---

*Báo cáo kỹ thuật được tạo từ mã nguồn thực tế của dự án SME Pulse.*
*Cập nhật lần cuối: 2025-01-15*

### 5.4 ML Training DAG

**Đường dẫn:** [airflow/dags/sme_pulse_ml_training.py](airflow/dags/sme_pulse_ml_training.py)

```python
# Schedule: Weekly (Sunday 1:00 AM)
with DAG('sme_pulse_ml_training', schedule_interval='0 1 * * 0') as dag:
    
    train_uc09_task = PythonOperator(
        task_id='train_uc09',
        python_callable=train_cashflow_model_uc09,  # Prophet
    )
    
    train_uc10_task = PythonOperator(
        task_id='train_uc10', 
        python_callable=train_anomaly_model_uc10,   # Isolation Forest
    )
    
    [train_uc09_task, train_uc10_task] >> validate_task
```

**Đường dẫn:** [ops/ml/UC09-forecasting/train_cashflow_model.py](ops/ml/UC09-forecasting/train_cashflow_model.py)

```python
def train_cashflow_forecast():
    mlflow.set_experiment("sme_pulse_cashflow_forecast")
    
    # Load data từ dbt "mâm cơm"
    conn = get_trino_connector()
    df = pd.read_sql("SELECT * FROM sme_lake.silver.ml_training_cashflow_fcst", conn)
    
    with mlflow.start_run():
        # Train Prophet với regressors
        model = Prophet(yearly_seasonality=True, weekly_seasonality=True)
        model.add_country_holidays(country_name='VN')
        for reg in ['is_weekend', 'is_holiday_vn', 'sin_month', 'cos_month']:
            model.add_regressor(reg)
        
        model.fit(df)
        
        # Cross-validation
        df_cv = cross_validation(model, horizon='30 days')
        mape = performance_metrics(df_cv)['mape'].mean()
        
        # Log to MLflow
        mlflow.log_metric("mape", mape)
        mlflow.prophet.log_model(model, "prophet_model", 
                                  registered_model_name="prophet_cashflow_v1")
```

---

## 6. BẢO MẬT & TIỆN ÍCH

### 6.1 Authentication Flow

**Đường dẫn:** [backend/app/core/security.py](backend/app/core/security.py)

```python
# Password hashing với bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT Token
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.BACKEND_SECRET_KEY, algorithm="HS256")

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.BACKEND_SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
```

**Đường dẫn:** [backend/app/modules/auth/dependencies.py](backend/app/modules/auth/dependencies.py)

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = int(payload.get("sub"))
    user = await db.execute(select(User).where(User.id == user_id))
    
    # Multi-tenancy check
    if payload.get("org_id") != user.org_id:
        raise HTTPException(status_code=401)
    
    return user

def requires_roles(allowed_roles: List[str]):
    """Role-based access control decorator"""
    async def role_checker(current_user = Depends(get_current_user)):
        user_roles = [ur.role.code for ur in current_user.roles]
        if not any(role in allowed_roles for role in user_roles):
            raise HTTPException(status_code=403, detail=f"Required role: {allowed_roles}")
        return current_user
    return role_checker
```

### 6.2 VietQR Integration

**Đường dẫn:** [frontend/src/components/Payments.tsx](frontend/src/components/Payments.tsx) (line 259-269)

```tsx
// Generate VietQR URL
const generateQRUrl = () => {
  if (!qrAmount || !qrDescription) return null;
  
  // VietQR format: https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-{TEMPLATE}.png
  const bankId = 'MB';
  const accountNo = '123456789';
  const template = 'compact2';
  
  return `https://img.vietqr.io/image/${bankId}-${accountNo}-${template}.png?amount=${qrAmount}&addInfo=${encodeURIComponent(qrDescription)}&accountName=CONG%20TY%20ABC`;
};

// Render QR
{qrUrl && <img src={qrUrl} alt="VietQR" className="w-48 h-48" />}
```

---

## 7. TÓM TẮT TECH STACK

| Layer | Technologies |
|-------|--------------|
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS, Shadcn/ui, React Query, Recharts |
| **Backend** | FastAPI, SQLAlchemy (Async), Pydantic, Celery |
| **Database** | PostgreSQL 15 (OLTP), Trino + Iceberg (OLAP) |
| **Data Lake** | MinIO (S3), dbt, Apache Iceberg |
| **ML/AI** | Prophet (Forecasting), Isolation Forest (Anomaly), MLflow |
| **Orchestration** | Apache Airflow |
| **BI** | Metabase (embedded) |
| **Auth** | JWT + bcrypt, RBAC (owner/accountant/cashier) |
| **Infra** | Docker Compose, Redis |

---

*Báo cáo được tạo tự động từ mã nguồn thực tế.*
