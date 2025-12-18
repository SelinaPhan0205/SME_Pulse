# SME Pulse – Frontend API Checklist

> Mục tiêu: Liệt kê toàn bộ API mà FE cần gọi, nhóm theo domain + file `services/*.ts`.  
> Mỗi API ghi: Method, Path, CRUD + dùng cho màn nào.

---

## 0. Gợi ý cấu trúc folder API

`src/lib/api/`
- `client.ts` – Axios client + interceptors
- `types.ts` – Kiểu dữ liệu chung
- `index.ts` – Re-export tất cả services

`src/lib/api/services/`
- `auth.ts`        – Login, current user, change password
- `users.ts`       – Quản lý user (User Management)
- `customers.ts`   – Master data khách hàng (AR)
- `suppliers.ts`   – Master data nhà cung cấp (AP)
- `accounts.ts`    – Tài khoản ngân hàng / tiền mặt (source của Payment)
- `invoices.ts`    – AR Invoices (Accounts Receivable)
- `bills.ts`       – AP Bills (Accounts Payable)
- `payments.ts`    – Payments + allocations
- `analytics.ts`   – KPIs, aging, reconciliation, Metabase token
- `reports.ts`     – Export reports (Excel/PDF)
- `settings.ts`    – Cấu hình AI, forecast, anomaly (màn Settings)

`src/lib/api/hooks/`
- `useAuth.ts`, `useUsers.ts`, `useCustomers.ts`, `useSuppliers.ts`,  
  `useAccounts.ts`, `useInvoices.ts`, `useBills.ts`, `usePayments.ts`,  
  `useAnalytics.ts`, `useReports.ts`, `useSettings.ts`

---

## 1. Auth & User

### 1.1 `auth.ts` – Authentication

**File:** `src/lib/api/services/auth.ts`  
**Dùng cho màn:** `Login.tsx`, `UserMenu.tsx`, Layout, bảo vệ route

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `login` | `POST /api/v1/auth/login` | **C** | Đăng nhập bằng email/password → trả về `access_token`, refresh token (nếu có). |
| 2 | `getCurrentUser` | `GET /api/v1/auth/me` | **R** | Lấy thông tin user hiện tại (email, name, roles, org_id) để hiển thị avatar, menu, RBAC. |
| 3 | `changePassword` | `POST /api/v1/auth/change-password` | **U** | User tự đổi mật khẩu trong màn Settings (input: old_password, new_password). |
| 4 | (optional) `logout` | (no backend hoặc `POST /api/v1/auth/logout`) | – | FE chỉ cần xoá token khỏi storage; nếu sau này làm revocation thì thêm endpoint. |

> Gợi ý: Mặc định dùng `/api/v1/auth/login` và `/api/v1/auth/me` đúng như backend.

---

### 1.2 `users.ts` – User Management (RBAC)

**File:** `src/lib/api/services/users.ts`  
**Dùng cho màn:** `UserManagement.tsx`

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getUsers` | `GET /api/v1/users` | **R** | Lấy danh sách user (có query: `search`, `role`, `status`, `page`, `page_size`) để render bảng User Management. |
| 2 | `getUserById` | `GET /api/v1/users/{id}` | **R** | Lấy chi tiết 1 user khi mở modal "Chỉnh sửa". |
| 3 | `createUser` | `POST /api/v1/users` | **C** | Tạo user mới (email, name, role, default password) từ modal "Thêm thành viên". |
| 4 | `updateUser` | `PUT /api/v1/users/{id}` | **U** | Cập nhật thông tin user: tên, role, trạng thái... |
| 5 | `deleteUser` (hoặc `deactivateUser`) | `DELETE /api/v1/users/{id}` | **D** | Deactivate user (soft delete, set `is_active = false`). Nút "Xoá/Ngưng hoạt động". |
| 6 | (optional) `resetUserPassword` | `POST /api/v1/users/{id}/reset-password` | **U** | Owner/Admin reset mật khẩu cho user khác. |

---

### 1.3 `settings.ts` – Account & AI Settings

**File:** `src/lib/api/services/settings.ts`  
**Dùng cho màn:** `Settings.tsx` (tab Cấu hình hệ thống / AI)

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getAISystemSettings` | `GET /api/v1/settings/ai` | **R** | Lấy config: forecast_window, confidence, seasonality, anomaly_threshold, min_amount, job schedule… để fill form Settings. |
| 2 | `updateAISystemSettings` | `PUT /api/v1/settings/ai` | **U** | Lưu lại config AI + forecast + anomaly từ màn Settings. |

---

## 2. Master Data – Customers, Suppliers, Accounts

### 2.1 `customers.ts` – Customers (AR)

**File:** `src/lib/api/services/customers.ts`  
**Dùng cho màn:** `AccountsReceivable.tsx` (filter theo khách), form tạo invoice, popup chọn customer.

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getCustomers` | `GET /api/v1/customers` | **R** | Danh sách khách hàng (query: `search`, `code`, `page`, `page_size`). |
| 2 | `getCustomerById` | `GET /api/v1/customers/{id}` | **R** | Lấy chi tiết 1 khách hàng khi xem thông tin trong popup. |
| 3 | `createCustomer` | `POST /api/v1/customers` | **C** | Tạo khách mới từ màn master data (hoặc trong popup "Thêm nhanh"). |
| 4 | `updateCustomer` | `PUT /api/v1/customers/{id}` | **U** | Cập nhật thông tin khách hàng. |
| 5 | `deleteCustomer` | `DELETE /api/v1/customers/{id}` | **D** | Soft delete khách hàng (không xoá hẳn). |

---

### 2.2 `suppliers.ts` – Suppliers (AP)

**File:** `src/lib/api/services/suppliers.ts`  
**Dùng cho màn:** `AccountsPayable.tsx` (lọc theo nhà cung cấp), future master data page.

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getSuppliers` | `GET /api/v1/suppliers` | **R** | Danh sách nhà cung cấp với pagination + search. |
| 2 | `getSupplierById` | `GET /api/v1/suppliers/{id}` | **R** | Lấy chi tiết 1 nhà cung cấp. |
| 3 | `createSupplier` | `POST /api/v1/suppliers` | **C** | Tạo nhà cung cấp mới. |
| 4 | `updateSupplier` | `PUT /api/v1/suppliers/{id}` | **U** | Update thông tin. |
| 5 | `deleteSupplier` | `DELETE /api/v1/suppliers/{id}` | **D** | Soft delete. |

---

### 2.3 `accounts.ts` – Bank / Cash Accounts

**File:** `src/lib/api/services/accounts.ts`  
**Dùng cho màn:** `Payments.tsx` (chọn nguồn tiền), (future) Settings/Accounts.

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getAccounts` | `GET /api/v1/accounts` | **R** | Lấy danh sách tài khoản ngân hàng / tiền mặt để hiển thị trong dropdown "Nguồn tiền". |
| 2 | `getAccountById` | `GET /api/v1/accounts/{id}` | **R** | Xem chi tiết 1 account (optional). |
| 3 | `createAccount` | `POST /api/v1/accounts` | **C** | Thêm tài khoản mới. |
| 4 | `updateAccount` | `PUT /api/v1/accounts/{id}` | **U** | Cập nhật thông tin account. |
| 5 | `deleteAccount` | `DELETE /api/v1/accounts/{id}` | **D** | Soft delete account. |

---

## 3. Finance – Accounts Receivable (AR Invoices)

### 3.1 `invoices.ts` – AR Invoices

**File:** `src/lib/api/services/invoices.ts`  
**Dùng cho màn:** `AccountsReceivable.tsx`, modal chi tiết hóa đơn, popup dòng công nợ, VietQR, Dashboard cards.

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getInvoices` | `GET /api/v1/invoices` | **R** | Lấy danh sách invoice AR, có query: `status` (draft/posted/partial/paid/overdue), `customer_id`, `due_from`, `due_to`, `overdue_only`, `search`, `page`, `page_size`, `risk_level`. |
| 2 | `getInvoiceById` | `GET /api/v1/invoices/{id}` | **R** | Lấy chi tiết invoice + allocations để hiện trong panel chi tiết. |
| 3 | `createInvoice` | `POST /api/v1/invoices` | **C** | Tạo invoice mới từ modal "Thêm hoá đơn". |
| 4 | `updateInvoice` | `PUT /api/v1/invoices/{id}` | **U** | Sửa invoice khi còn `status = draft`. |
| 5 | `deleteInvoice` | `DELETE /api/v1/invoices/{id}` | **D** | Xoá/huỷ invoice draft (soft delete). |
| 6 | `postInvoice` | `POST /api/v1/invoices/{id}/post` | **U** | Thay đổi trạng thái invoice từ `draft` → `posted` (chốt hoá đơn, cho phép nhận thanh toán). |

---

## 4. Finance – Accounts Payable (AP Bills)

### 4.1 `bills.ts` – AP Bills

**File:** `src/lib/api/services/bills.ts`  
**Dùng cho màn:** `AccountsPayable.tsx` (giống AR nhưng là phải trả nhà cung cấp).

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getBills` | `GET /api/v1/bills` | **R** | Lấy danh sách bill (AP) với filter tương tự invoices: status, supplier_id, due range, search, page. |
| 2 | `getBillById` | `GET /api/v1/bills/{id}` | **R** | Chi tiết 1 bill. |
| 3 | `createBill` | `POST /api/v1/bills` | **C** | Tạo bill mới. |
| 4 | `updateBill` | `PUT /api/v1/bills/{id}` | **U** | Sửa bill khi còn draft. |
| 5 | `deleteBill` | `DELETE /api/v1/bills/{id}` | **D** | Soft delete bill. |
| 6 | `postBill` | `POST /api/v1/bills/{id}/post` | **U** | Chốt bill (cho phép payment ra). |

---

## 5. Finance – Payments & Bank Reconciliation

### 5.1 `payments.ts` – Payments + Allocations

**File:** `src/lib/api/services/payments.ts`  
**Dùng cho màn:** `Payments.tsx`, modal tạo thanh toán, panel chi tiết thanh toán.

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getPayments` | `GET /api/v1/payments` | **R** | Lấy danh sách thanh toán (query: `date_from`, `date_to`, `customer_id`, `account_id`, `has_allocations`, `page`, `page_size`). |
| 2 | `getPaymentById` | `GET /api/v1/payments/{id}` | **R** | Lấy chi tiết payment + allocations (dùng cho panel chi tiết ở Payments). |
| 3 | `createPayment` | `POST /api/v1/payments` | **C** | Tạo payment mới + allocations (mapping tới nhiều invoice). Backend update `paid_amount` + `status` của invoice. |

---

### 5.2 (Optional) Bank Reconciliation APIs

Nếu muốn làm phần **đối soát ngân hàng** thật (thay mock):

**File:** `src/lib/api/services/reconciliation.ts` hoặc gộp vào `payments.ts`.

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 4 | `getBankTransactions` | `GET /api/v1/reconciliation/bank-transactions` | **R** | Lấy danh sách bank transactions (status: `unmatched`, `matched`, `suspicious`) để fill bảng. |
| 5 | `importBankFile` | `POST /api/v1/reconciliation/import-bank-file` | **C** | Upload file sao kê (CSV/Excel) → backend parse + lưu tạm. |
| 6 | `runAutoMatch` | `POST /api/v1/reconciliation/auto-match` | **C** | Chạy job auto-matching giữa bank_txn và payments/invoices. |
| 7 | `getReconciliationSummary` | `GET /api/v1/analytics/kpi/reconciliation` | **R** | Đã có backend – thống kê: tổng giao dịch, đã đối soát, pending → KPI. |

---

## 6. Analytics & Dashboard

### 6.1 `analytics.ts` – Core KPIs + Aging

**File:** `src/lib/api/services/analytics.ts`  
**Dùng cho màn:** `Dashboard.tsx`, `RevenueChart.tsx`, `AccountsReceivable.tsx`, `AccountsPayable.tsx`, `Payments.tsx`

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getDashboardSummary` | `GET /api/v1/analytics/summary` | **R** | Dashboard cards: DSO, DPO, CCC, tổng AR/AP, số invoice quá hạn, tổng payment… |
| 2 | `getARAging` | `GET /api/v1/analytics/aging/ar` | **R** | Aging report AR theo bucket (0–30, 31–60, 61–90, 90+). Dùng cho màn AR & Reports. |
| 3 | `getAPAging` | `GET /api/v1/analytics/aging/ap` | **R** | Aging report AP tương tự cho Accounts Payable. |
| 4 | `getDailyRevenue` | `GET /api/v1/analytics/kpi/daily-revenue` | **R** | Time-series doanh thu theo ngày cho `RevenueChart.tsx`, Dashboard line chart, Forecast base line. |
| 5 | `getPaymentSuccessRate` | `GET /api/v1/analytics/kpi/payment-success-rate` | **R** | Tỷ lệ thanh toán thành công để vẽ donut/badge ở Dashboard/Payments. |
| 6 | `getReconciliationKPI` | `GET /api/v1/analytics/kpi/reconciliation` | **R** | KPI đối soát (matched/pending) cho Dashboard và vùng đối soát. |

---

### 6.2 `analytics.ts` – Metabase embedding (Forecast & Anomaly dashboards)

**File:** vẫn `analytics.ts` (thêm group Metabase)  
**Dùng cho màn:** `Forecast.tsx` (embed dashboard Cashflow Forecast), `AnomalyDetection.tsx` (embed dashboard Anomaly)

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 7 | `getMetabaseToken` | `GET /api/v1/analytics/metabase-token?resource_id=2&resource_type=dashboard` | **R** | Lấy `embed_url` cho dashboard Forecast (Cashflow). |
| 8 | `getAnomalyMetabaseToken` | `GET /api/v1/analytics/metabase-token?resource_id=5&resource_type=dashboard` | **R** | Lấy `embed_url` cho dashboard Anomaly. |

---

### 6.3 (Optional) Raw Forecast & Anomaly series

Nếu muốn vẽ chart custom (không chỉ embed Metabase):

**File:** có thể tách `forecast.ts` + `anomalies.ts` hoặc để chung `analytics.ts`.

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 9 | `getRevenueForecast` | `GET /api/v1/analytics/forecast/revenue` | **R** | Trả về actual + forecast + upper/lower bound cho `ForecastChart.tsx` và `ForecastDetailChart.tsx`. |
| 10 | `getRevenueAnomalies` | `GET /api/v1/analytics/anomalies/revenue` | **R** | Danh sách điểm bất thường theo ngày: amount, expected, deviation, severity… dùng cho `AnomalyChart.tsx`, `AnomalyDetection.tsx`. |

---

## 7. Alerts / Anomalies List

Nếu muốn màn `AnomalyDetection.tsx` hiển thị bảng alert:

**File:** `src/lib/api/services/alerts.ts` *hoặc* gộp vào `analytics.ts`.

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getAlerts` | `GET /api/v1/alerts` (hoặc `/api/v1/analytics/alerts`) | **R** | Lấy danh sách alert / anomaly (loại: overdue_invoice, high_risk_customer, abnormal_payment...). |
| 2 | `getAlertById` | `GET /api/v1/alerts/{id}` | **R** | Chi tiết một alert khi user bấm xem. |
| 3 | `markAlertRead` | `PUT /api/v1/alerts/{id}` | **U** | Đánh dấu alert đã đọc. |
| 4 | (optional) `snoozeAlert` | `POST /api/v1/alerts/{id}/snooze` | **U** | Tạm ẩn alert (nếu muốn làm “Snooze”). |

---

## 8. Reports & Export Jobs

### 8.1 `reports.ts` – Report templates & export history

**File:** `src/lib/api/services/reports.ts`  
**Dùng cho màn:** `Reports.tsx` (bảng danh sách report, nút "Generate", "Download")

| # | API | Method & Path | CRUD | Mục đích |
|---|-----|---------------|------|----------|
| 1 | `getReportTemplates` | `GET /api/v1/analytics/reports/templates` | **R** | Danh sách loại report: `AR Aging`, `AP Aging`, `AR Detail`, `Payments`, `Cashflow Forecast`… (có description, slug, supported formats). |
| 2 | `createExportJob` | `POST /api/v1/analytics/reports/export` | **C** | Tạo job export (body: `report_type`, `format`, `filters`), trả về `job_id`, `status`. |
| 3 | `getExportJobs` | `GET /api/v1/analytics/reports/export-jobs` | **R** | List lịch sử export: report_type, format, status, created_at, created_by, file_url (nếu xong). |
| 4 | `getExportJobById` | `GET /api/v1/analytics/reports/export-jobs/{id}` | **R** | Query status 1 job cụ thể, dùng để polling khi user vừa bấm Generate. |

> Nút **Generate**: gọi `createExportJob` → hiển thị status.  
> Nút **Download**: lấy `file_url` từ job rồi `window.open(file_url)`.

---

## 9. Mapping nhanh: màn → service nào?

- `LandingPage.tsx` – **không cần API**, chỉ static.
- `Login.tsx` – `auth.ts` (`login`).
- `Sidebar.tsx` – `auth.ts` (`getCurrentUser`) để hiển thị tên/org.
- `UserMenu.tsx` – `auth.ts` (`getCurrentUser`, `logout` FE, `changePassword`).
- `Dashboard.tsx` – `analytics.ts` (summary, daily-revenue, payment-success-rate, reconciliation, aging).
- `RevenueChart.tsx` – `analytics.ts` (`getDailyRevenue`).
- `AccountsReceivable.tsx` – `invoices.ts`, `customers.ts`, `analytics.ts` (ARAging), optional `alerts.ts`.
- `AccountsPayable.tsx` – `bills.ts`, `suppliers.ts`, `analytics.ts` (APAging).
- `Payments.tsx` – `payments.ts`, `customers.ts`, `accounts.ts`, optional `reconciliation.ts` + `analytics.ts` (reconciliation KPI).
- `AnomalyChart.tsx`, `AnomalyDetection.tsx` – `analytics.ts` (anomalies hoặc Metabase token), optional `alerts.ts`.
- `Forecast.tsx`, `ForecastChart.tsx`, `ForecastDetailChart.tsx` – `analytics.ts` (daily-revenue, forecast, Metabase token).
- `Reports.tsx` – `analytics.ts` (aging + KPIs) + `reports.ts` (createExportJob, list history).
- `UserManagement.tsx` – `users.ts`.
- `Settings.tsx` – `settings.ts`, `auth.ts` (`changePassword`).

