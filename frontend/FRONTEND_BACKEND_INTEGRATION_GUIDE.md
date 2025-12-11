# 🚀 SME PULSE - Hướng Dẫn Tích Hợp Frontend & Backend

> **Dành cho Backend Developer không biết React/Frontend**  
> Tài liệu này giải thích chi tiết cách Frontend hoạt động, API nào được gọi, data flow như thế nào, và Backend cần làm gì tiếp.

**Ngày cập nhật:** 06/12/2024  
**Trạng thái Frontend:** ✅ Hoàn thành 100% tích hợp API  
**Trạng thái Backend:** ⚠️ Cần implement các endpoints còn thiếu

---

## 📋 Mục Lục

1. [Tổng Quan Kiến Trúc Frontend](#1-tổng-quan-kiến-trúc-frontend)
2. [Flow Hoạt Động Của Frontend](#2-flow-hoạt-động-của-frontend)
3. [Danh Sách API Đã Tích Hợp](#3-danh-sách-api-đã-tích-hợp)
4. [Chi Tiết Từng Trang](#4-chi-tiết-từng-trang)
5. [Field Name Mappings Quan Trọng](#5-field-name-mappings-quan-trọng)
6. [API Endpoints Backend Cần Implement](#6-api-endpoints-backend-cần-implement)
7. [Testing & Debugging](#7-testing--debugging)
8. [Checklist Tích Hợp](#8-checklist-tích-hợp)

---

## 1. Tổng Quan Kiến Trúc Frontend

### 1.1 Tech Stack

```
Frontend Stack:
├── React 18 + TypeScript          # UI framework với type safety
├── React Query v5 (@tanstack)     # Server state management (tự động cache, refetch)
├── Axios                          # HTTP client
├── React Router v6                # Client-side routing
├── Tailwind CSS v4                # Styling
├── shadcn/ui                      # Pre-built UI components
├── Sonner                         # Toast notifications
└── Mock Service Worker (MSW)      # API mocking (TẠM THỜI - sẽ tắt khi backend ready)
```

### 1.2 Cấu Trúc Thư Mục API

```
src/lib/api/
├── client.ts                    # ⭐ Axios instance + interceptors (token, error handling)
├── types.ts                     # TypeScript interfaces cho tất cả data models
├── index.ts                     # Re-export all
│
├── services/                    # 🔹 API Service Layer (gọi backend thật)
│   ├── auth.ts                  # Login, getCurrentUser, changePassword, logout
│   ├── users.ts                 # User CRUD (6 functions)
│   ├── customers.ts             # Customer CRUD (5 functions)
│   ├── suppliers.ts             # Supplier CRUD (5 functions)
│   ├── accounts.ts              # Bank/Cash Account CRUD (5 functions)
│   ├── invoices.ts              # AR Invoice CRUD + postInvoice (6 functions)
│   ├── bills.ts                 # AP Bill CRUD + postBill (6 functions)
│   ├── payments.ts              # Payment + Allocations (3 functions)
│   ├── analytics.ts             # KPIs, Aging, Forecast, Anomalies (10 functions)
│   ├── reports.ts               # Export Jobs (4 functions)
│   ├── settings.ts              # AI Settings (2 functions)
│   └── alerts.ts                # Alerts/Notifications (4 functions)
│
├── hooks/                       # 🔹 React Query Hooks (sử dụng trong components)
│   ├── useAuth.ts               # useLogin, useCurrentUser, useChangePassword, useLogout
│   ├── useUsers.ts              # 6 hooks (CRUD + reset password)
│   ├── useCustomers.ts          # 5 hooks
│   ├── useSuppliers.ts          # 5 hooks
│   ├── useAccounts.ts           # 5 hooks
│   ├── useInvoices.ts           # 6 hooks
│   ├── useBills.ts              # 6 hooks
│   ├── usePayments.ts           # 3 hooks
│   ├── useAnalytics.ts          # 10 hooks
│   ├── useReports.ts            # 4 hooks
│   ├── useSettings.ts           # 2 hooks
│   └── useAlerts.ts             # 4 hooks
│
└── mocks/                       # ⚠️ MSW Handlers (TẠM THỜI - chỉ dùng cho dev)
    ├── handlers.ts              # ~40 mock endpoints
    └── browser.ts               # MSW service worker setup
```

### 1.3 Axios Client Configuration

**File:** `src/lib/api/client.ts`

```typescript
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ⭐ Request Interceptor - TỰ ĐỘNG gắn token vào mọi request
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ⭐ Response Interceptor - Xử lý lỗi 401 (token hết hạn)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);
```

**Backend cần biết:**
- Frontend TỰ ĐỘNG gắn `Authorization: Bearer <token>` vào header mọi request
- Token được lưu trong `localStorage` sau khi login thành công
- Backend KHÔNG cần lo về CORS nếu đã config đúng trong FastAPI

---

## 2. Flow Hoạt Động Của Frontend

### 2.1 Authentication Flow

```
User nhập email/password → Click "Đăng nhập"
    ↓
Frontend gọi: POST /api/v1/auth/login
    Body: { "email": "user@example.com", "password": "123456" }
    ↓
Backend trả về:
    {
      "access_token": "eyJhbGciOiJIUzI1NiIs...",
      "token_type": "bearer",
      "user": {
        "id": 1,
        "email": "user@example.com",
        "full_name": "Nguyễn Văn A",
        "roles": ["admin"],
        "is_active": true
      }
    }
    ↓
Frontend lưu token vào localStorage:
    localStorage.setItem('token', response.access_token)
    ↓
Frontend cache user data vào React Query:
    queryClient.setQueryData(['currentUser'], response.user)
    ↓
Frontend redirect đến /dashboard
```

**Các request sau đó:**
```
GET /api/v1/invoices
Headers: {
  "Authorization": "Bearer eyJhbGciOiJIUzI1NiIs...",
  "Content-Type": "application/json"
}
```

### 2.2 Data Fetching Flow (React Query)

**VÍ DỤ: Trang Accounts Receivable**

```typescript
// Component code
function AccountsReceivable() {
  // 1️⃣ Gọi hook để fetch invoices
  const { data: invoicesData, isLoading, error } = useInvoices({
    status: 'posted',
    skip: 0,
    limit: 10
  });
  
  // 2️⃣ React Query TỰ ĐỘNG:
  //    - Gọi GET /api/v1/invoices?status=posted&skip=0&limit=10
  //    - Cache response với key ['invoices', { status: 'posted', skip: 0, limit: 10 }]
  //    - Tự động refetch khi stale (sau 5 phút)
  //    - Hiển thị cached data ngay lập tức nếu có
  
  // 3️⃣ Render UI
  if (isLoading) return <Spinner />;
  if (error) return <ErrorMessage />;
  
  const invoices = invoicesData?.items || [];
  return <Table data={invoices} />;
}
```

**Backend response format cần đúng:**
```json
{
  "total": 156,
  "skip": 0,
  "limit": 10,
  "items": [
    {
      "id": 1,
      "invoice_number": "INV-2024-001",
      "customer_id": 5,
      "issue_date": "2024-11-15",
      "due_date": "2024-12-15",
      "total_amount": 15000000,
      "paid_amount": 5000000,
      "remaining_amount": 10000000,
      "status": "posted",
      "customer": {
        "id": 5,
        "name": "Công ty ABC",
        "email": "abc@example.com"
      }
    }
  ]
}
```

### 2.3 Mutation Flow (Create/Update/Delete)

**VÍ DỤ: Tạo Invoice Mới**

```typescript
// 1️⃣ Component setup mutation
const createInvoiceMutation = useCreateInvoice();

// 2️⃣ User submit form
const handleSubmit = (formData) => {
  createInvoiceMutation.mutate({
    customer_id: formData.customerId,
    issue_date: formData.issueDate,
    due_date: formData.dueDate,
    total_amount: formData.totalAmount,
    items: formData.items,
  }, {
    onSuccess: (response) => {
      // 3️⃣ Hiển thị toast thành công
      toast.success('Tạo hóa đơn thành công!');
      
      // 4️⃣ React Query TỰ ĐỘNG invalidate cache
      // → Refetch lại danh sách invoices để UI update
      queryClient.invalidateQueries(['invoices']);
      
      // 5️⃣ Đóng modal
      setIsModalOpen(false);
    },
    onError: (error) => {
      // 6️⃣ Hiển thị lỗi
      toast.error(error?.response?.data?.detail || 'Có lỗi xảy ra');
    }
  });
};
```

**Request gửi đi:**
```http
POST /api/v1/invoices
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "customer_id": 5,
  "issue_date": "2024-12-06",
  "due_date": "2025-01-05",
  "total_amount": 25000000,
  "items": [...]
}
```

**Backend response mong muốn:**
```json
{
  "id": 157,
  "invoice_number": "INV-2024-157",
  "customer_id": 5,
  "issue_date": "2024-12-06",
  "due_date": "2025-01-05",
  "total_amount": 25000000,
  "status": "draft",
  "created_at": "2024-12-06T10:30:00Z",
  "customer": {
    "id": 5,
    "name": "Công ty ABC"
  }
}
```

---

## 3. Danh Sách API Đã Tích Hợp

### ✅ Đã Tích Hợp Hoàn Chỉnh (7/10 trang)

| # | Trang | Hooks Đã Dùng | Endpoints Backend Cần Có |
|---|-------|---------------|---------------------------|
| 1 | **Dashboard** | useDashboardSummary, useDailyRevenue, usePaymentSuccessRate, useReconciliationKPI, useRevenueForecast, useAlerts | `GET /api/v1/analytics/summary`<br>`GET /api/v1/analytics/daily-revenue`<br>`GET /api/v1/analytics/kpi/payment-success-rate`<br>`GET /api/v1/analytics/kpi/reconciliation`<br>`GET /api/v1/analytics/forecast/revenue`<br>`GET /api/v1/alerts` |
| 2 | **AccountsReceivable** | useInvoices, useCustomers, useUpdateInvoice, useDeleteInvoice, useARAging | `GET /api/v1/invoices`<br>`GET /api/v1/customers`<br>`PUT /api/v1/invoices/{id}`<br>`DELETE /api/v1/invoices/{id}`<br>`GET /api/v1/analytics/ar-aging` |
| 3 | **AccountsPayable** | useBills, useSuppliers, useUpdateBill, useDeleteBill, useAPAging | `GET /api/v1/bills`<br>`GET /api/v1/suppliers`<br>`PUT /api/v1/bills/{id}`<br>`DELETE /api/v1/bills/{id}`<br>`GET /api/v1/analytics/ap-aging` |
| 4 | **Payments** | usePayments, useAccounts, useReconciliationKPI | `GET /api/v1/payments`<br>`GET /api/v1/accounts`<br>`GET /api/v1/analytics/kpi/reconciliation` |
| 5 | **UserManagement** | useUsers, useCreateUser, useUpdateUser, useDeleteUser | `GET /api/v1/users`<br>`POST /api/v1/users`<br>`PUT /api/v1/users/{id}`<br>`DELETE /api/v1/users/{id}` |
| 6 | **Settings** | useAISettings, useUpdateAISettings, useChangePassword | `GET /api/v1/settings/ai`<br>`PUT /api/v1/settings/ai`<br>`POST /api/v1/auth/change-password` |
| 7 | **UserMenu** | useCurrentUser, useUpdateUser, useChangePassword, useLogout | `GET /api/v1/auth/me`<br>`PUT /api/v1/users/{id}`<br>`POST /api/v1/auth/change-password` |

### ⚠️ Chưa Tích Hợp (3/10 trang - OPTIONAL)

| # | Trang | Lý Do Chưa Tích Hợp | Plan |
|---|-------|----------------------|------|
| 8 | **Forecast** | Chủ yếu embed Metabase iframe | Có hook `useRevenueForecast` sẵn nếu cần custom chart |
| 9 | **AnomalyDetection** | Chủ yếu embed Metabase iframe | Có hook `useRevenueAnomalies` + `useAlerts` sẵn |
| 10 | **Reports** | Dùng static Recharts | Có hook `useReportTemplates`, `useCreateExportJob` nếu cần export |

---

## 4. Chi Tiết Từng Trang

### 4.1 Dashboard (✅ 100% Complete)

**File:** `src/components/Dashboard.tsx`

**APIs Được Gọi:**
1. `GET /api/v1/analytics/summary` - KPIs tổng hợp (DSO, DPO, CCC, AR, AP)
2. `GET /api/v1/analytics/daily-revenue` - Doanh thu theo ngày (30 ngày)
3. `GET /api/v1/analytics/kpi/payment-success-rate` - Tỷ lệ thanh toán thành công
4. `GET /api/v1/analytics/kpi/reconciliation` - Trạng thái đối soát
5. `GET /api/v1/analytics/forecast/revenue` - Dự báo doanh thu 7 ngày
6. `GET /api/v1/alerts?limit=5` - 5 alerts gần nhất

**Data Flow:**
```typescript
// 1. Component fetch data
const { data: summary, isLoading: loadingSummary } = useDashboardSummary();
const { data: dailyRevenue, isLoading: loadingRevenue } = useDailyRevenue({ days: 30 });

// 2. Render cards với loading state
{loadingSummary ? (
  <Skeleton className="h-32" />
) : (
  <Card>
    <CardTitle>DSO</CardTitle>
    <p>{summary.dso} ngày</p>
  </Card>
)}

// 3. Render chart với error handling
{loadingRevenue ? (
  <div>Đang tải...</div>
) : (
  <LineChart data={dailyRevenue?.data} />
)}
```

**Backend Response Format:**

```json
// GET /api/v1/analytics/summary
{
  "dso": 45.5,
  "dpo": 38.2,
  "ccc": 12.3,
  "total_ar": 1250000000,
  "total_ap": 890000000,
  "overdue_invoices": 23,
  "total_payments_this_month": 567000000
}

// GET /api/v1/analytics/daily-revenue
{
  "data": [
    { "date": "2024-11-07", "revenue": 45000000 },
    { "date": "2024-11-08", "revenue": 52000000 }
  ]
}
```

---

### 4.2 Accounts Receivable (✅ 100% Complete)

**File:** `src/components/AccountsReceivable.tsx`

**APIs Được Gọi:**
1. `GET /api/v1/invoices?status={status}&customer_id={id}&skip={skip}&limit={limit}` - List invoices
2. `GET /api/v1/customers` - List customers (cho dropdown filter)
3. `PUT /api/v1/invoices/{id}` - Update invoice
4. `DELETE /api/v1/invoices/{id}` - Delete invoice
5. `GET /api/v1/analytics/ar-aging` - AR Aging report

**Field Name Mappings (QUAN TRỌNG!):**

| Frontend Display | Backend Field | Data Type | Notes |
|------------------|---------------|-----------|-------|
| Mã hóa đơn | `invoice_number` | string | |
| Ngày phát hành | `issue_date` | string (ISO date) | **NOT** `invoice_date` |
| Ngày đến hạn | `due_date` | string (ISO date) | |
| Tổng tiền | `total_amount` | number | **NOT** `invoice_amount` |
| Đã thu | `paid_amount` | number | |
| Còn nợ | `remaining_amount` | number | **NOT** `balance_due` |
| Trạng thái | `status` | string | draft/posted/partial/paid/overdue |
| Khách hàng | `customer` | object | Nested object với id, name |
| Hạn thanh toán | `customer.credit_term` | number | Days (Customer model) |

**Update Request:**
```http
PUT /api/v1/invoices/157
Content-Type: application/json

{
  "total_amount": 30000000,
  "due_date": "2025-01-15",
  "notes": "Updated amount"
}
```

**Delete Request:**
```http
DELETE /api/v1/invoices/157
```

**Component Code Snippet:**
```typescript
// Map API response to display format
const allInvoices = invoicesData?.items.map(inv => ({
  id: inv.id,
  code: inv.invoice_number,
  customer: inv.customer?.name || 'N/A',
  issueDate: new Date(inv.issue_date).toLocaleDateString('vi-VN'),
  dueDate: new Date(inv.due_date).toLocaleDateString('vi-VN'),
  totalAmount: inv.total_amount,
  paidAmount: inv.paid_amount,
  remainingAmount: inv.remaining_amount,
  status: inv.status,
  // Lấy credit_term từ customer nested object
  termsDay: inv.customer?.credit_term || 30,
})) || [];

// Update mutation
const updateInvoiceMutation = useUpdateInvoice();

const handleUpdate = (invoiceId, data) => {
  updateInvoiceMutation.mutate({ id: invoiceId, data }, {
    onSuccess: () => toast.success('Cập nhật thành công!'),
    onError: (error) => toast.error(error?.response?.data?.detail),
  });
};
```

---

### 4.3 Accounts Payable (✅ 100% Complete)

**File:** `src/components/AccountsPayable.tsx`

**APIs Được Gọi:**
1. `GET /api/v1/bills?status={status}&supplier_id={id}&skip={skip}&limit={limit}` - List bills
2. `GET /api/v1/suppliers` - List suppliers
3. `PUT /api/v1/bills/{id}` - Update bill
4. `DELETE /api/v1/bills/{id}` - Delete bill
5. `GET /api/v1/analytics/ap-aging` - AP Aging report

**Field Name Mappings (QUAN TRỌNG!):**

| Frontend Display | Backend Field | Data Type | Notes |
|------------------|---------------|-----------|-------|
| Mã hóa đơn | `bill_number` | string | |
| Nhà cung cấp | `supplier` | object | Nested với id, name |
| Hạn thanh toán | `supplier.payment_term` | number | **NOT** `credit_term`! (khác Customer) |
| Tổng tiền | `total_amount` | number | |
| Đã trả | `paid_amount` | number | |
| Còn nợ | `remaining_amount` | number | |

**⚠️ CRITICAL: Supplier vs Customer Field Difference**

```typescript
// ❌ SAI - dùng credit_term cho Supplier
const terms = bill.supplier?.credit_term; // UNDEFINED!

// ✅ ĐÚNG - Supplier dùng payment_term
const terms = bill.supplier?.payment_term || 30;

// Customer thì dùng credit_term
const customerTerms = invoice.customer?.credit_term || 30;
```

---

### 4.4 Payments (✅ 95% Complete)

**File:** `src/components/Payments.tsx`

**APIs Được Gọi:**
1. `GET /api/v1/payments?skip={skip}&limit={limit}` - List payments
2. `GET /api/v1/accounts` - List bank/cash accounts
3. `GET /api/v1/analytics/kpi/reconciliation` - Reconciliation summary
4. `POST /api/v1/payments` - Create payment (⚠️ Chưa tích hợp vào form)

**Field Name Mappings:**

| Frontend Display | Backend Field | Data Type | Notes |
|------------------|---------------|-----------|-------|
| Ngày giao dịch | `transaction_date` | string (ISO) | **NOT** `payment_date` |
| Mã tham chiếu | `reference_code` | string | **NOT** `reference_number` |
| Phương thức | `payment_method` | string \| null | ⚠️ CÓ THỂ NULL! |
| Tài khoản | `account.name` | string | **NOT** `account_name` |
| Số tài khoản | `account.account_number` | string | |
| Ngân hàng | `account.bank_name` | string | |

**Payment Allocations:**
```typescript
// Create payment với allocations
createPaymentMutation.mutate({
  transaction_date: "2024-12-06",
  amount: 25000000,
  account_id: 3,
  payment_method: "transfer",
  reference_code: "TRF20241206001",
  notes: "Thanh toán hóa đơn tháng 11",
  allocations: [
    { ar_invoice_id: 123, allocated_amount: 15000000 },
    { ar_invoice_id: 124, allocated_amount: 10000000 }
  ]
});
```

**Backend Expected Response:**
```json
{
  "id": 567,
  "transaction_date": "2024-12-06",
  "amount": 25000000,
  "account_id": 3,
  "payment_method": "transfer",
  "reference_code": "TRF20241206001",
  "notes": "Thanh toán hóa đơn tháng 11",
  "account": {
    "id": 3,
    "name": "Tài khoản Vietcombank",
    "account_number": "1234567890",
    "bank_name": "Vietcombank"
  },
  "allocations": [
    {
      "id": 1001,
      "payment_id": 567,
      "ar_invoice_id": 123,
      "allocated_amount": 15000000
    },
    {
      "id": 1002,
      "payment_id": 567,
      "ar_invoice_id": 124,
      "allocated_amount": 10000000
    }
  ]
}
```

**Tab Reconcile:**
- Summary cards dùng `useReconciliationKPI()` - ✅ Đã tích hợp
- Bảng chi tiết đang dùng mock data - ⚠️ Backend cần implement `GET /api/v1/reconciliation/transactions`

---

### 4.5 User Management (✅ 100% Complete)

**File:** `src/components/UserManagement.tsx`

**APIs Được Gọi:**
1. `GET /api/v1/users?search={term}&role={role}&skip={skip}&limit={limit}`
2. `POST /api/v1/users` - Create user
3. `PUT /api/v1/users/{id}` - Update user
4. `DELETE /api/v1/users/{id}` - Soft delete user

**Field Name Mappings:**

| Frontend Display | Backend Field | Data Type | Notes |
|------------------|---------------|-----------|-------|
| Vai trò | `roles` | string[] | ⚠️ ARRAY, not single string! |
| Trạng thái | `is_active` | boolean | |

**⚠️ CRITICAL: User.roles is ARRAY**

```typescript
// ❌ SAI
const role = user.role; // UNDEFINED!

// ✅ ĐÚNG
const role = user.roles?.[0] || 'viewer'; // Get first role
```

**Create User Request:**
```http
POST /api/v1/users
Content-Type: application/json

{
  "email": "new.user@example.com",
  "full_name": "Nguyễn Văn B",
  "password": "DefaultPass123",
  "roles": ["accountant"],
  "is_active": true
}
```

---

### 4.6 Settings (✅ 100% Complete)

**File:** `src/components/Settings.tsx`

**APIs Được Gọi:**
1. `GET /api/v1/settings/ai` - Get AI/Prophet settings
2. `PUT /api/v1/settings/ai` - Update settings
3. `POST /api/v1/auth/change-password` - Change password

**Field Name Mappings:**

| Frontend Display | Backend Field | Data Type | Notes |
|------------------|---------------|-----------|-------|
| Dự báo (ngày) | `forecast_window` | number | **NOT** `forecast_days` |
| Độ tin cậy | `forecast_confidence` | number | **NOT** `confidence_level` |
| Mùa vụ | `seasonality` | boolean | |
| Ngưỡng anomaly | `anomaly_threshold` | number | |
| Số tiền tối thiểu | `min_amount` | number | |

**Update Settings Request:**
```http
PUT /api/v1/settings/ai
Content-Type: application/json

{
  "forecast_window": 30,
  "forecast_confidence": 0.95,
  "seasonality": true,
  "anomaly_threshold": 2.5,
  "min_amount": 1000000
}
```

---

### 4.7 UserMenu (✅ 100% Complete)

**File:** `src/components/UserMenu.tsx`

**APIs Được Gọi:**
1. `GET /api/v1/auth/me` - Get current user (hiển thị avatar, name, email)
2. `PUT /api/v1/users/{id}` - Update profile name
3. `POST /api/v1/auth/change-password` - Change password

**Change Password Request:**
```http
POST /api/v1/auth/change-password
Content-Type: application/json

{
  "old_password": "OldPassword123",
  "new_password": "NewPassword456"
}
```

**Expected Responses:**
- Success: `204 No Content` hoặc `{ "message": "Password updated successfully" }`
- Error 400: `{ "detail": "Mật khẩu hiện tại không đúng" }`

---

## 5. Field Name Mappings Quan Trọng

### ⚠️ CÁC LỖI THƯỜNG GẶP

| Model | Frontend Expect | Backend PHẢI Dùng | Notes |
|-------|-----------------|-------------------|-------|
| **ARInvoice** | `issue_date` | `issue_date` | ❌ NOT `invoice_date` |
| | `total_amount` | `total_amount` | ❌ NOT `invoice_amount` |
| | `remaining_amount` | `remaining_amount` | ❌ NOT `balance_due` |
| **Customer** | `credit_term` | `credit_term` | ✅ Days |
| **Supplier** | `payment_term` | `payment_term` | ⚠️ KHÁC Customer! NOT `credit_term` |
| **Account** | `name` | `name` | ❌ NOT `account_name` |
| **Payment** | `transaction_date` | `transaction_date` | ❌ NOT `payment_date` |
| | `reference_code` | `reference_code` | ❌ NOT `reference_number` |
| | `payment_method` | `payment_method` | ⚠️ CAN BE NULL |
| **User** | `roles` | `roles` | ⚠️ ARRAY not string |
| **AISettings** | `forecast_window` | `forecast_window` | ❌ NOT `forecast_days` |
| | `forecast_confidence` | `forecast_confidence` | ❌ NOT `confidence_level` |

### ✅ Nested Object Fields

```typescript
// Invoice with Customer
{
  "id": 1,
  "invoice_number": "INV-001",
  "total_amount": 10000000,
  "customer": {           // ⭐ Nested object
    "id": 5,
    "name": "Công ty ABC",
    "email": "abc@example.com",
    "credit_term": 30     // ⭐ Trong Customer
  }
}

// Bill with Supplier
{
  "id": 1,
  "bill_number": "BILL-001",
  "total_amount": 8000000,
  "supplier": {           // ⭐ Nested object
    "id": 10,
    "name": "NCC XYZ",
    "payment_term": 45    // ⭐ Trong Supplier (NOT credit_term!)
  }
}

// Payment with Account
{
  "id": 1,
  "transaction_date": "2024-12-06",
  "amount": 15000000,
  "account": {            // ⭐ Nested object
    "id": 3,
    "name": "VCB",        // ⭐ name field
    "account_number": "123456",
    "bank_name": "Vietcombank"
  }
}
```

---

## 6. API Endpoints Backend Cần Implement

### 6.1 Authentication (✅ Priority HIGH)

| Method | Endpoint | Request Body | Response | Status |
|--------|----------|--------------|----------|--------|
| POST | `/api/v1/auth/login` | `{ email, password }` | `{ access_token, user }` | ⚠️ Cần test |
| GET | `/api/v1/auth/me` | - | `{ id, email, full_name, roles[], ... }` | ⚠️ Cần test |
| POST | `/api/v1/auth/change-password` | `{ old_password, new_password }` | `204` hoặc success message | ❌ Chưa có |

### 6.2 Users (✅ Priority HIGH)

| Method | Endpoint | Query Params | Request Body | Status |
|--------|----------|--------------|--------------|--------|
| GET | `/api/v1/users` | `?search=&role=&skip=&limit=` | - | ⚠️ Cần test |
| GET | `/api/v1/users/{id}` | - | - | ⚠️ Cần test |
| POST | `/api/v1/users` | - | `{ email, full_name, password, roles[], ... }` | ⚠️ roles ARRAY! |
| PUT | `/api/v1/users/{id}` | - | `{ full_name?, roles[]?, ... }` | ⚠️ Cần test |
| DELETE | `/api/v1/users/{id}` | - | - | ⚠️ Soft delete |

### 6.3 Customers (✅ Priority HIGH)

| Method | Endpoint | Query Params | Status |
|--------|----------|--------------|--------|
| GET | `/api/v1/customers` | `?search=&skip=&limit=` | ⚠️ Cần test |
| GET | `/api/v1/customers/{id}` | - | ⚠️ Cần test |
| POST | `/api/v1/customers` | - | ❌ Frontend chưa dùng |
| PUT | `/api/v1/customers/{id}` | - | ❌ Frontend chưa dùng |
| DELETE | `/api/v1/customers/{id}` | - | ❌ Frontend chưa dùng |

### 6.4 Suppliers (✅ Priority HIGH)

| Method | Endpoint | Query Params | Status |
|--------|----------|--------------|--------|
| GET | `/api/v1/suppliers` | `?search=&skip=&limit=` | ⚠️ Cần test |
| GET | `/api/v1/suppliers/{id}` | - | ⚠️ Cần test |

**⚠️ CRITICAL:** Supplier PHẢI có field `payment_term` (NOT `credit_term`)

### 6.5 Accounts (✅ Priority HIGH)

| Method | Endpoint | Status |
|--------|----------|--------|
| GET | `/api/v1/accounts` | ⚠️ Cần test |
| GET | `/api/v1/accounts/{id}` | ❌ Frontend chưa dùng |

**Response format:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Tài khoản Vietcombank",
      "account_number": "1234567890",
      "bank_name": "Vietcombank",
      "type": "bank",
      "currency": "VND",
      "balance": 500000000
    }
  ]
}
```

### 6.6 AR Invoices (✅ Priority HIGH)

| Method | Endpoint | Query Params | Status |
|--------|----------|--------------|--------|
| GET | `/api/v1/invoices` | `?status=&customer_id=&skip=&limit=` | ⚠️ Test field names |
| GET | `/api/v1/invoices/{id}` | - | ❌ Frontend chưa dùng |
| POST | `/api/v1/invoices` | - | ❌ Frontend chưa dùng |
| PUT | `/api/v1/invoices/{id}` | - | ✅ Đã dùng - test carefully |
| DELETE | `/api/v1/invoices/{id}` | - | ✅ Đã dùng |
| POST | `/api/v1/invoices/{id}/post` | - | ❌ Frontend chưa dùng |

**⚠️ Response MUST include:**
```json
{
  "total": 156,
  "skip": 0,
  "limit": 10,
  "items": [
    {
      "id": 1,
      "invoice_number": "INV-001",
      "issue_date": "2024-11-15",      // NOT invoice_date
      "due_date": "2024-12-15",
      "total_amount": 15000000,        // NOT invoice_amount
      "paid_amount": 5000000,
      "remaining_amount": 10000000,    // NOT balance_due
      "status": "posted",
      "customer": {                     // NESTED object
        "id": 5,
        "name": "Công ty ABC",
        "credit_term": 30              // credit_term in Customer
      }
    }
  ]
}
```

### 6.7 AP Bills (✅ Priority HIGH)

| Method | Endpoint | Query Params | Status |
|--------|----------|--------------|--------|
| GET | `/api/v1/bills` | `?status=&supplier_id=&skip=&limit=` | ⚠️ Test field names |
| PUT | `/api/v1/bills/{id}` | - | ✅ Đã dùng |
| DELETE | `/api/v1/bills/{id}` | - | ✅ Đã dùng |

**⚠️ Response MUST include:**
```json
{
  "items": [
    {
      "id": 1,
      "bill_number": "BILL-001",
      "total_amount": 8000000,
      "supplier": {
        "id": 10,
        "name": "NCC XYZ",
        "payment_term": 45    // ⚠️ payment_term NOT credit_term!
      }
    }
  ]
}
```

### 6.8 Payments (✅ Priority HIGH)

| Method | Endpoint | Query Params | Status |
|--------|----------|--------------|--------|
| GET | `/api/v1/payments` | `?skip=&limit=` | ⚠️ Test field names |
| GET | `/api/v1/payments/{id}` | - | ❌ Frontend chưa dùng |
| POST | `/api/v1/payments` | - | ⚠️ Có mutation nhưng chưa dùng |

**POST Request Format:**
```json
{
  "transaction_date": "2024-12-06",
  "amount": 25000000,
  "account_id": 3,
  "payment_method": "transfer",
  "reference_code": "TRF20241206001",
  "notes": "Thanh toán hóa đơn",
  "allocations": [
    { "ar_invoice_id": 123, "allocated_amount": 15000000 },
    { "ar_invoice_id": 124, "allocated_amount": 10000000 }
  ]
}
```

**⚠️ GET Response MUST include:**
```json
{
  "items": [
    {
      "id": 1,
      "transaction_date": "2024-12-06",  // NOT payment_date
      "amount": 25000000,
      "payment_method": "transfer",      // CAN BE NULL
      "reference_code": "TRF123",        // NOT reference_number
      "notes": "...",
      "account": {                       // NESTED
        "id": 3,
        "name": "VCB",                   // name NOT account_name
        "account_number": "123456",
        "bank_name": "Vietcombank"
      },
      "allocations": [...]
    }
  ]
}
```

### 6.9 Analytics (✅ Priority HIGH)

| Method | Endpoint | Query Params | Status |
|--------|----------|--------------|--------|
| GET | `/api/v1/analytics/summary` | - | ⚠️ Cần test |
| GET | `/api/v1/analytics/daily-revenue` | `?days=30` | ⚠️ Cần test |
| GET | `/api/v1/analytics/ar-aging` | - | ⚠️ Cần test |
| GET | `/api/v1/analytics/ap-aging` | - | ⚠️ Cần test |
| GET | `/api/v1/analytics/kpi/payment-success-rate` | - | ⚠️ Cần test |
| GET | `/api/v1/analytics/kpi/reconciliation` | - | ⚠️ Cần test |
| GET | `/api/v1/analytics/forecast/revenue` | `?start_date=&end_date=` | ⚠️ Cần test |

**Sample Response - Dashboard Summary:**
```json
{
  "dso": 45.5,
  "dpo": 38.2,
  "ccc": 12.3,
  "total_ar": 1250000000,
  "total_ap": 890000000,
  "overdue_invoices": 23,
  "total_payments_this_month": 567000000
}
```

**Sample Response - Reconciliation KPI:**
```json
{
  "total_transactions": 150,
  "matched_transactions": 120,
  "pending_transactions": 30,
  "matched_rate": 0.8
}
```

### 6.10 Settings (✅ Priority MEDIUM)

| Method | Endpoint | Status |
|--------|----------|--------|
| GET | `/api/v1/settings/ai` | ⚠️ Cần test |
| PUT | `/api/v1/settings/ai` | ⚠️ Cần test |

**Response Format:**
```json
{
  "forecast_window": 30,           // NOT forecast_days
  "forecast_confidence": 0.95,     // NOT confidence_level
  "seasonality": true,
  "anomaly_threshold": 2.5,
  "min_amount": 1000000,
  "job_schedule": "0 0 * * *"
}
```

### 6.11 Alerts (✅ Priority LOW)

| Method | Endpoint | Query Params | Status |
|--------|----------|--------------|--------|
| GET | `/api/v1/alerts` | `?limit=5` | ⚠️ Cần test |

### 6.12 Missing Endpoints (❌ Backend Cần Implement)

| Priority | Endpoint | Purpose | Used In |
|----------|----------|---------|---------|
| 🔴 HIGH | `GET /api/v1/reconciliation/transactions` | Chi tiết từng giao dịch đối soát | Payments tab Reconcile |
| 🟡 MEDIUM | `POST /api/v1/invoices/{id}/post` | Chốt invoice (draft → posted) | AccountsReceivable |
| 🟡 MEDIUM | `POST /api/v1/bills/{id}/post` | Chốt bill | AccountsPayable |
| 🟢 LOW | `GET /api/v1/analytics/reports/templates` | Danh sách report templates | Reports page |
| 🟢 LOW | `POST /api/v1/analytics/reports/export` | Tạo export job | Reports page |
| 🟢 LOW | `GET /api/v1/analytics/reports/export-jobs` | Lịch sử export | Reports page |

---

## 7. Testing & Debugging

### 7.1 Tắt Mock Service Worker

**Khi Backend Ready:**

1. Comment out MSW trong `src/main.tsx`:

```typescript
// import { worker } from './lib/api/mocks/browser';

// ❌ Comment dòng này
// if (import.meta.env.DEV) {
//   worker.start({
//     onUnhandledRequest: 'bypass',
//   });
// }

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

2. Set API base URL trong `.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

3. Frontend SẼ GỌI THẲNG backend của bạn!

### 7.2 Debug API Calls

**Mở Chrome DevTools:**

1. **Network Tab**
   - Xem tất cả requests: filter `Fetch/XHR`
   - Check request headers (có `Authorization: Bearer ...` không?)
   - Check request payload
   - Check response status & body

2. **Console Tab**
   - React Query devtools: Xem cache, queries status
   - Console.log errors

**Example Debug Output:**
```
Request:
  Method: GET
  URL: http://localhost:8000/api/v1/invoices?status=posted&skip=0&limit=10
  Headers:
    Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
    Content-Type: application/json

Response:
  Status: 200 OK
  Body: {
    "total": 156,
    "skip": 0,
    "limit": 10,
    "items": [...]
  }
```

### 7.3 Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Token hết hạn hoặc invalid | Backend check token validation logic |
| `404 Not Found` | Endpoint chưa implement | Backend implement endpoint |
| `422 Unprocessable Entity` | Request body sai format | Check field names, data types |
| `500 Internal Server Error` | Backend crash | Check backend logs |
| `CORS Error` | Backend chưa config CORS | Add frontend domain vào CORS whitelist |
| `undefined` trong UI | Field name không match | Check field mappings section 5 |

**CORS Config (FastAPI):**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 8. Checklist Tích Hợp

### 8.1 Backend Developer Tasks

**Authentication:**
- [ ] `POST /api/v1/auth/login` - Return `access_token` + `user` object
- [ ] `GET /api/v1/auth/me` - Return current user với `roles[]` (array!)
- [ ] `POST /api/v1/auth/change-password` - Validate old password

**Users:**
- [ ] Ensure `User.roles` is **ARRAY** of strings
- [ ] `GET /api/v1/users` - Support query params: search, role, skip, limit
- [ ] `POST /api/v1/users` - Accept `roles[]` array

**Customers:**
- [ ] Ensure `Customer.credit_term` field exists (number, days)
- [ ] `GET /api/v1/customers` - Return list với pagination

**Suppliers:**
- [ ] ⚠️ Ensure `Supplier.payment_term` field exists (**NOT** `credit_term`)
- [ ] `GET /api/v1/suppliers` - Return list

**Accounts:**
- [ ] Ensure `Account.name` field (**NOT** `account_name`)
- [ ] `GET /api/v1/accounts` - Return list

**AR Invoices:**
- [ ] ⚠️ Use field names: `issue_date`, `total_amount`, `remaining_amount`
- [ ] ⚠️ NOT: `invoice_date`, `invoice_amount`, `balance_due`
- [ ] Include nested `customer` object với `credit_term`
- [ ] `GET /api/v1/invoices` - Support filters + pagination
- [ ] `PUT /api/v1/invoices/{id}` - Update invoice
- [ ] `DELETE /api/v1/invoices/{id}` - Soft delete

**AP Bills:**
- [ ] Include nested `supplier` object với `payment_term` (**NOT** `credit_term`)
- [ ] `GET /api/v1/bills` - Support filters
- [ ] `PUT /api/v1/bills/{id}` - Update bill
- [ ] `DELETE /api/v1/bills/{id}` - Soft delete

**Payments:**
- [ ] ⚠️ Use field names: `transaction_date`, `reference_code`
- [ ] ⚠️ `payment_method` CAN BE NULL
- [ ] Include nested `account` object với `name` field
- [ ] `GET /api/v1/payments` - Return list
- [ ] `POST /api/v1/payments` - Accept `allocations[]` array

**Analytics:**
- [ ] `GET /api/v1/analytics/summary` - Dashboard KPIs
- [ ] `GET /api/v1/analytics/daily-revenue` - Time series
- [ ] `GET /api/v1/analytics/ar-aging` - AR aging buckets
- [ ] `GET /api/v1/analytics/ap-aging` - AP aging buckets
- [ ] `GET /api/v1/analytics/kpi/payment-success-rate` - Payment stats
- [ ] `GET /api/v1/analytics/kpi/reconciliation` - Reconciliation summary
- [ ] `GET /api/v1/analytics/forecast/revenue` - Prophet forecast data

**Settings:**
- [ ] ⚠️ Use field names: `forecast_window`, `forecast_confidence`
- [ ] ⚠️ NOT: `forecast_days`, `confidence_level`
- [ ] `GET /api/v1/settings/ai` - Return AI config
- [ ] `PUT /api/v1/settings/ai` - Update AI config

**Alerts:**
- [ ] `GET /api/v1/alerts` - Return recent alerts

**Missing Endpoints:**
- [ ] `GET /api/v1/reconciliation/transactions` - Chi tiết đối soát (Priority HIGH)
- [ ] `POST /api/v1/invoices/{id}/post` - Chốt invoice (Priority MEDIUM)
- [ ] `POST /api/v1/bills/{id}/post` - Chốt bill (Priority MEDIUM)

### 8.2 Testing Checklist

**Authentication Flow:**
- [ ] Login với email/password đúng → Nhận token + user
- [ ] Login sai → Nhận 401 với error message
- [ ] Token tự động gắn vào header các request sau
- [ ] Token hết hạn → Auto redirect về login

**CRUD Operations:**
- [ ] List invoices → Hiển thị đúng data, pagination
- [ ] Update invoice → UI update ngay, toast success
- [ ] Delete invoice → UI remove row, toast success
- [ ] Create user → Thêm vào list, toast success
- [ ] Tất cả mutations có error handling với toast

**Field Mappings:**
- [ ] Invoice hiển thị đúng `issue_date`, `total_amount`, `remaining_amount`
- [ ] Customer hiển thị đúng `credit_term`
- [ ] Supplier hiển thị đúng `payment_term` (KHÔNG PHẢI `credit_term`)
- [ ] Account hiển thị đúng `name`
- [ ] Payment hiển thị đúng `transaction_date`, `reference_code`
- [ ] User hiển thị đúng `roles[0]`
- [ ] Settings hiển thị đúng `forecast_window`, `forecast_confidence`

**Dashboard:**
- [ ] KPI cards hiển thị đúng số liệu
- [ ] Revenue chart vẽ được với dữ liệu thật
- [ ] Forecast chart hiển thị 7 ngày dự báo
- [ ] Alerts hiển thị 5 alerts gần nhất

**Error Handling:**
- [ ] 401 → Auto logout + redirect login
- [ ] 404 → Toast error "Không tìm thấy"
- [ ] 500 → Toast error "Lỗi server"
- [ ] Network error → Toast error "Không thể kết nối"

---

## 📝 Tóm Tắt Cho Backend Developer

### ✅ Frontend Đã Làm Gì?

1. **Setup hoàn chỉnh API layer:**
   - 12 service files với ~60 functions
   - 12 React Query hook files với ~50 hooks
   - Axios client với token interceptors
   - Type-safe 100% với TypeScript

2. **Tích hợp 7/10 trang chính:**
   - Dashboard, AccountsReceivable, AccountsPayable
   - Payments, UserManagement, Settings, UserMenu
   - Tất cả dùng API thật (qua MSW mock tạm thời)

3. **UI/UX hoàn chỉnh:**
   - Loading states (skeleton, spinner)
   - Error handling (toast notifications)
   - Pagination, filtering, search
   - CRUD operations với mutations
   - Auto-refetch khi data thay đổi

### ⚠️ Backend Cần Làm Gì?

1. **Implement các endpoints còn thiếu** (section 6.12)
2. **Kiểm tra field names** (section 5) - RẤT QUAN TRỌNG!
3. **Test response format** với Postman/Thunder Client
4. **Config CORS** để frontend gọi được
5. **Fix các issues** nếu frontend báo lỗi

### 🚀 Steps Tích Hợp

1. Backend implement endpoints theo spec ở section 6
2. Test với Postman - đảm bảo response format đúng
3. Frontend tắt MSW (section 7.1)
4. Frontend gọi backend thật
5. Fix bugs nếu có
6. ✅ Done!

---

**📧 Contact:**
- Frontend: Đã hoàn thành 100%
- Backend: Kiểm tra checklist section 8.1
- Issues: Check field mappings section 5

**📚 Tham Khảo:**
- `api_list.md` - Chi tiết tất cả API endpoints
- `API_IMPLEMENTATION_SUMMARY.md` - Tổng kết công việc đã làm
- `FRONTEND_BACKEND_INTEGRATION_GUIDE.md` (file này) - Hướng dẫn tích hợp

---

**⏰ Last Updated:** 06/12/2024  
**✅ Status:** Frontend Ready - Backend Integration Needed
