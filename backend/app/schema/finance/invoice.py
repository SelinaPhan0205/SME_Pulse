"""Schema Hóa đơn AR."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, computed_field


class InvoiceBase(BaseModel):
    """Schema cơ bản cho Hóa đơn AR."""
    invoice_no: str = Field(..., min_length=1, max_length=50, description="Invoice number")
    customer_id: int = Field(..., gt=0, description="Customer ID")
    issue_date: date = Field(..., description="Invoice issue date")
    due_date: date = Field(..., description="Payment due date")
    total_amount: Decimal = Field(..., gt=0, decimal_places=2, description="Total invoice amount")
    notes: Optional[str] = Field(None, description="Additional notes")


class InvoiceCreate(InvoiceBase):
    """Schema cho việc tạo Hóa đơn AR (luôn bắt đầu với trạng thái NHÁP)."""
    pass


class InvoiceUpdate(BaseModel):
    """Schema cho việc cập nhật Hóa đơn AR (chỉ cho phép khi ở trạng thái NHÁP)."""
    invoice_no: Optional[str] = Field(None, min_length=1, max_length=50)
    customer_id: Optional[int] = Field(None, gt=0)
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    total_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    notes: Optional[str] = None


class InvoicePost(BaseModel):
    """Schema cho việc đăng Hóa đơn (chuyên NHÁP → ĐĂNG)."""
    pass  # No fields needed, just triggers state change


class InvoiceResponse(InvoiceBase):
    """Schema cho phản hồi Hóa đơn AR."""
    id: int
    org_id: int
    status: str = Field(..., description="draft, posted, partial, paid, overdue, cancelled")
    paid_amount: Decimal = Field(..., description="Amount already paid")
    created_at: datetime
    updated_at: datetime
    
    @computed_field
    @property
    def remaining_amount(self) -> Decimal:
        """Tính toán số dư chưa thanh toán."""
        return self.total_amount - self.paid_amount
    
    model_config = {"from_attributes": True}


class PaginatedInvoicesResponse(BaseModel):
    """Phản hồi có phân trang cho danh sách hóa đơn."""
    total: int
    skip: int
    limit: int
    items: list[InvoiceResponse]


# ==================== BULK IMPORT SCHEMAS ====================

class InvoiceBulkImportItem(BaseModel):
    """Schema cho một hóa đơn trong nhập khẩu hàng loạt."""
    invoice_no: str = Field(..., min_length=1, max_length=50, description="Invoice number")
    customer_id: int = Field(..., gt=0, description="Customer ID")
    issue_date: date = Field(..., description="Invoice issue date")
    due_date: date = Field(..., description="Payment due date")
    total_amount: Decimal = Field(..., gt=0, decimal_places=2, description="Total invoice amount")
    notes: Optional[str] = Field(None, description="Additional notes")


class InvoiceBulkImportRequest(BaseModel):
    """Schema cho yêu cầu nhập khẩu hàng loạt hóa đơn."""
    invoices: list[InvoiceBulkImportItem] = Field(..., min_length=1, max_length=100, description="List of invoices to import")
    auto_post: bool = Field(False, description="Automatically post invoices after creation")


class InvoiceBulkImportResultItem(BaseModel):
    """Kết quả cho một hóa đơn trong nhập khẩu hàng loạt."""
    invoice_no: str
    success: bool
    id: Optional[int] = None
    error: Optional[str] = None


class InvoiceBulkImportResponse(BaseModel):
    """Phản hồi cho nhập khẩu hàng loạt hóa đơn."""
    total_submitted: int
    total_success: int
    total_failed: int
    results: list[InvoiceBulkImportResultItem]
