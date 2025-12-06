/**
 * API Types & Interfaces
 * Định nghĩa types cho request/response theo backend schemas
 */

// ============================================================
// AUTH TYPES
// ============================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserInfo {
  id: number;
  email: string;
  full_name: string | null;
  org_id: number;
  status: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserInfo;
  roles: string[];
}

export interface UserResponse {
  id: number;
  email: string;
  full_name: string | null;
  org_id: number;
  status: string;
  roles: string[];
}

// ============================================================
// CUSTOMER TYPES
// ============================================================

export interface CustomerBase {
  name: string;
  code?: string | null;
  tax_code?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  credit_term: number;
  is_active: boolean;
}

export interface CustomerCreate extends CustomerBase {}

export interface CustomerUpdate {
  name?: string;
  code?: string | null;
  tax_code?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  credit_term?: number;
  is_active?: boolean;
}

export interface CustomerResponse extends CustomerBase {
  id: number;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface PaginatedCustomersResponse {
  total: number;
  skip: number;
  limit: number;
  items: CustomerResponse[];
}

// ============================================================
// SUPPLIER TYPES (tương tự Customer)
// ============================================================

export interface SupplierBase {
  name: string;
  code?: string | null;
  tax_code?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  payment_term: number;
  is_active: boolean;
}

export interface SupplierCreate extends SupplierBase {}

export interface SupplierUpdate {
  name?: string;
  code?: string | null;
  tax_code?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  payment_term?: number;
  is_active?: boolean;
}

export interface SupplierResponse extends SupplierBase {
  id: number;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface PaginatedSuppliersResponse {
  total: number;
  skip: number;
  limit: number;
  items: SupplierResponse[];
}

// ============================================================
// ANALYTICS TYPES
// ============================================================

export interface DashboardSummary {
  total_revenue: number;
  total_receivables: number;
  total_payables: number;
  payment_success_rate: number;
  overdue_invoices_count: number;
  pending_payments_count: number;
}

export interface ARAgingBucket {
  bucket: string;
  amount: number;
  count: number;
}

export interface ARAgingResponse {
  total_ar: number;
  buckets: ARAgingBucket[];
}

export interface APAgingBucket {
  bucket: string;
  amount: number;
  count: number;
}

export interface APAgingResponse {
  total_ap: number;
  buckets: APAgingBucket[];
}

export interface DailyRevenuePoint {
  date: string;
  revenue: number;
}

export interface DailyRevenueResponse {
  data: DailyRevenuePoint[];
}

export interface PaymentSuccessRateResponse {
  success_rate: number;
  total_payments: number;
  successful_payments: number;
}

// ============================================================
// COMMON TYPES
// ============================================================

export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export interface DateRangeParams {
  start_date?: string; // YYYY-MM-DD
  end_date?: string;   // YYYY-MM-DD
}

export interface ErrorResponse {
  detail: string;
  error_code?: string;
}
