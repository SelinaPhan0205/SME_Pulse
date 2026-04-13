"""Schema phân tích - Các mô hình phản hồi Pydantic cho KPI và báo cáo."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


# ============================================================
# SCHEMAS KPI & BẢNG ĐIỀU KHIỂN
# ============================================================

class AgingBucketDetail(BaseModel):
    """Phân tích một khoảng lão hóa."""
    bucket_days: str = Field(..., description="Aging bucket: '0-30', '31-60', '61-90', '>90'")
    count: int = Field(..., ge=0, description="Number of invoices/bills in this bucket")
    total_amount: Decimal = Field(..., ge=0, description="Total amount in this bucket (VND)")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of total")


class DashboardSummary(BaseModel):
    """Tóm tắt KPI bảng điều khiển - Dữ liệu thực tế từ App DB."""
    dso: float = Field(..., description="Days Sales Outstanding")
    dpo: float = Field(..., description="Days Payable Outstanding")
    ccc: float = Field(..., description="Cash Conversion Cycle = DSO - DPO")
    total_ar: Decimal = Field(..., ge=0, description="Total Accounts Receivable (VND)")
    total_ap: Decimal = Field(..., ge=0, description="Total Accounts Payable (VND)")
    cash_balance: Decimal = Field(..., description="Current cash balance (VND)")
    working_capital: Decimal = Field(..., description="Working Capital = Cash + AR - AP (VND)")
    overdue_ar_count: int = Field(..., ge=0, description="Number of overdue AR invoices")
    overdue_ar_amount: Decimal = Field(..., ge=0, description="Total overdue AR amount (VND)")
    overdue_ap_count: int = Field(..., ge=0, description="Number of overdue AP bills")
    overdue_ap_amount: Decimal = Field(..., ge=0, description="Total overdue AP amount (VND)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")
    
    model_config = {"from_attributes": True}


class ARAgingResponse(BaseModel):
    """Báo cáo lão hóa AR - Phân tích theo ngày đề hạn."""
    total_ar: Decimal = Field(..., ge=0, description="Total AR amount (VND)")
    total_invoices: int = Field(..., ge=0, description="Total number of invoices")
    buckets: List[AgingBucketDetail] = Field(..., description="Aging breakdown by bucket")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")


class APAgingResponse(BaseModel):
    """Báo cáo lão hóa AP - Phân tích theo ngày đề hạn."""
    total_ap: Decimal = Field(..., ge=0, description="Total AP amount (VND)")
    total_bills: int = Field(..., ge=0, description="Total number of bills")
    buckets: List[AgingBucketDetail] = Field(..., description="Aging breakdown by bucket")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")


class DailyRevenueDataPoint(BaseModel):
    """Một điểm dữ liệu doanh thu hàng ngày."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    revenue: Decimal = Field(..., ge=0, description="Revenue for this day (VND)")


class DailyRevenueResponse(BaseModel):
    """KPI Doanh thu hàng ngày - N ngày gần đây."""
    total_revenue: Decimal = Field(..., ge=0, description="Total revenue in period (VND)")
    average_daily_revenue: Decimal = Field(..., ge=0, description="Average daily revenue (VND)")
    data: List[DailyRevenueDataPoint] = Field(..., description="Daily breakdown")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")


class PaymentSuccessRateResponse(BaseModel):
    """KPI Tỷ lệ Thanh toán thành công."""
    success_rate: float = Field(..., ge=0, le=100, description="Percentage of successful payments")
    total_transactions: int = Field(..., ge=0, description="Total payment transactions")
    successful: int = Field(..., ge=0, description="Number of successful payments")
    failed: int = Field(..., ge=0, description="Number of failed payments")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")


class ReconciliationDiscrepancy(BaseModel):
    """Một ngoại lệ sức Điều hòa."""
    transaction_id: int = Field(..., description="Transaction ID")
    amount_expected: Decimal = Field(..., description="Expected amount (VND)")
    amount_received: Decimal = Field(..., description="Actual received amount (VND)")
    difference: Decimal = Field(..., description="Difference amount (VND)")


class ReconciliationResponse(BaseModel):
    """Trạng thái Điều hòa Thanh toán."""
    total_transactions: int = Field(..., ge=0, description="Total transactions for date")
    reconciled: int = Field(..., ge=0, description="Number of reconciled transactions")
    pending: int = Field(..., ge=0, description="Number of pending reconciliation")
    reconciliation_rate: float = Field(..., ge=0, le=100, description="Percentage reconciled")
    discrepancies: List[ReconciliationDiscrepancy] = Field(..., description="List of discrepancies")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")


# ============================================================
# SCHEMA CÔNG VIỆC XUẤT
# ============================================================

class ExportJobResponse(BaseModel):
    """Phản hồi trạng thái công việc xuất."""
    job_id: str = Field(..., description="Unique job ID")
    status: str = Field(..., description="pending, running, completed, failed")
    report_type: str = Field(..., description="ar_aging, ap_aging, cashflow, payment")
    format: str = Field(..., description="xlsx or pdf")
    file_url: Optional[str] = Field(None, description="Download URL if completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation time")
    updated_at: datetime = Field(..., description="Last update time")
    
    model_config = {"from_attributes": True}


# ============================================================
# SCHEMA NHÚNG METABASE
# ============================================================

class MetabaseTokenResponse(BaseModel):
    """Phản hồi JWT token nhúng ngắm tất Metabase."""
    token: str = Field(..., description="JWT token for Metabase embedding")
    embed_url: str = Field(..., description="Full embed URL for iframe")
    dashboard_id: int = Field(..., description="Metabase dashboard ID")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    
    model_config = {"from_attributes": True}


# ============================================================
# SCHEMAS DỰ BÁO ML & PHÁT HIỆN BẤT THƯỜNG
# ============================================================

class ForecastPoint(BaseModel):
    """Một điểm dữ liệu dự báo dòng tiền."""
    date: str = Field(..., description="Forecast date in YYYY-MM-DD format")
    actual: Optional[float] = Field(None, description="Actual cashflow if available (historical data)")
    forecast: float = Field(..., description="Predicted cashflow (VND)")
    lower_bound: float = Field(..., description="Lower confidence bound (VND)")
    upper_bound: float = Field(..., description="Upper confidence bound (VND)")


class ForecastResponse(BaseModel):
    """Phản hồi dự báo doanh thu - Các dự đoán ML Prophet."""
    data: List[ForecastPoint] = Field(..., description="Forecast data points")
    model_name: Optional[str] = Field(None, description="ML model name")
    total_days: int = Field(..., ge=0, description="Number of forecast days")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Prediction generation time")


class AnomalyPoint(BaseModel):
    """Một cảnh báo phát hiện bất thường."""
    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    amount: float = Field(..., description="Transaction amount (VND)")
    expected: Optional[float] = Field(None, description="Expected amount based on historical patterns")
    deviation: float = Field(..., description="Anomaly score (negative values indicate anomaly)")
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    category: Optional[str] = Field(None, description="Transaction category")
    counterparty: Optional[str] = Field(None, description="Counterparty name")


class AnomalyResponse(BaseModel):
    """Phản hồi phát hiện bất thường doanh thu - Các cảnh báo ML Isolation Forest."""
    data: List[AnomalyPoint] = Field(..., description="Anomaly alerts")
    total_anomalies: int = Field(..., ge=0, description="Total number of anomalies detected")
    severity_breakdown: Optional[dict] = Field(None, description="Count by severity level")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Detection time")


# ============================================================
# SCHEMA HÀNH ĐỘNG ĐIỀU HÒA
# ============================================================

class ReconciliationMatch(BaseModel):
    """Một cặp giao dịch khớp."""
    bank_transaction_id: int = Field(..., description="Bank transaction ID")
    payment_id: int = Field(..., description="System payment ID")
    bank_amount: Decimal = Field(..., description="Bank transaction amount")
    payment_amount: Decimal = Field(..., description="System payment amount")
    match_confidence: float = Field(..., ge=0, le=100, description="Match confidence percentage")
    status: str = Field(..., description="matched, pending, rejected")


class ReconciliationAutoMatchResponse(BaseModel):
    """Phản hồi kết quả tự-khớp."""
    total_bank_transactions: int = Field(..., ge=0)
    total_matched: int = Field(..., ge=0)
    total_unmatched: int = Field(..., ge=0)
    matches: List[ReconciliationMatch] = Field(default_factory=list)
    unmatched_bank_ids: List[int] = Field(default_factory=list)
    unmatched_payment_ids: List[int] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReconciliationConfirmRequest(BaseModel):
    """Yêu cầu xác nhận một khớp điều hòa."""
    bank_transaction_id: int = Field(..., description="Bank transaction ID")
    payment_id: int = Field(..., description="System payment ID to match")
    notes: Optional[str] = Field(None, description="Optional notes")


class ReconciliationActionResponse(BaseModel):
    """Phản hồi cho các hành động xác nhận/từ chối điều hòa."""
    success: bool = Field(..., description="Whether action succeeded")
    message: str = Field(..., description="Action result message")
    transaction_id: int = Field(..., description="Affected transaction ID")
    new_status: str = Field(..., description="New reconciliation status")
