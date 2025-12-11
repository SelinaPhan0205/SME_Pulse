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
  dso: number;  // Days Sales Outstanding
  dpo: number;  // Days Payable Outstanding
  ccc: number;  // Cash Conversion Cycle
  total_ar: number;  // Total Accounts Receivable
  total_ap: number;  // Total Accounts Payable
  cash_balance: number;
  working_capital: number;
  overdue_ar_count: number;
  overdue_ar_amount: number;
  overdue_ap_count: number;
  overdue_ap_amount: number;
  timestamp: string;
  // Legacy fields for backwards compatibility
  total_revenue?: number;
  total_receivables?: number;
  total_payables?: number;
  payment_success_rate?: number;
  overdue_invoices_count?: number;
  pending_payments_count?: number;
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

// ============================================================
// ANALYTICS & ML TYPES
// ============================================================

// Forecast API Types (UC09 - Prophet Cashflow Forecasting)
export interface ForecastPoint {
  date: string;              // YYYY-MM-DD
  actual?: number | null;    // Historical cashflow (VND)
  forecast: number;          // Predicted cashflow (VND)
  lower_bound: number;       // 95% confidence lower bound (VND)
  upper_bound: number;       // 95% confidence upper bound (VND)
}

export interface ForecastResponse {
  data: ForecastPoint[];
  model_name: string;        // e.g., "prophet_cashflow_v1"
  total_days: number;        // Number of forecast points
  timestamp: string;         // ISO datetime when generated
}

// Anomaly API Types (UC10 - Isolation Forest Anomaly Detection)
export interface AnomalyPoint {
  date: string;              // YYYY-MM-DD
  amount: number;            // Transaction amount (VND)
  expected: number;          // Expected amount (VND)
  deviation: number;         // Anomaly score (negative = anomaly)
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;          // e.g., "REVENUE", "EXPENSE", "OTHER_INCOME"
  counterparty?: string;     // Customer/Supplier name (optional)
}

export interface AnomalyResponse {
  data: AnomalyPoint[];
  total_anomalies: number;
  severity_breakdown: {      // Count by severity level
    CRITICAL?: number;
    HIGH?: number;
    MEDIUM?: number;
    LOW?: number;
  };
  timestamp: string;         // ISO datetime
}

// Metabase Embedding
export interface MetabaseTokenResponse {
  embed_url: string;         // Signed Metabase dashboard URL
  expires_at: string;        // ISO datetime
}

// Bank Reconciliation KPI
export interface ReconciliationKPI {
  total_transactions: number;
  matched: number;
  unmatched: number;
  suspicious: number;
  match_rate: number;        // Percentage (0-100)
}

// ============================================================
// RECONCILIATION ACTION TYPES
// ============================================================

export interface ReconciliationMatch {
  bank_transaction_id: number;
  payment_id: number;
  bank_amount: number;
  payment_amount: number;
  match_confidence: number;  // 0-100
  status: 'matched' | 'pending' | 'rejected';
}

export interface ReconciliationAutoMatchResponse {
  total_bank_transactions: number;
  total_matched: number;
  total_unmatched: number;
  matches: ReconciliationMatch[];
  unmatched_bank_ids: number[];
  unmatched_payment_ids: number[];
  timestamp: string;
}

export interface ReconciliationConfirmRequest {
  bank_transaction_id: number;
  payment_id: number;
  notes?: string;
}

export interface ReconciliationActionResponse {
  success: boolean;
  message: string;
  transaction_id: number;
  new_status: string;
}

export interface PendingTransaction {
  id: number;
  date: string;
  amount: number;
  reference?: string;
  type: 'bank' | 'payment';
}

export interface PendingReconciliationsResponse {
  date: string;
  pending_count: number;
  transactions: PendingTransaction[];
}

export interface ErrorResponse {
  detail: string;
  error_code?: string;
}
