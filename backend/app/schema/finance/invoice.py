"""AR Invoice schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, computed_field


class InvoiceBase(BaseModel):
    """Base schema for AR Invoice."""
    invoice_no: str = Field(..., min_length=1, max_length=50, description="Invoice number")
    customer_id: int = Field(..., gt=0, description="Customer ID")
    issue_date: date = Field(..., description="Invoice issue date")
    due_date: date = Field(..., description="Payment due date")
    total_amount: Decimal = Field(..., gt=0, decimal_places=2, description="Total invoice amount")
    notes: Optional[str] = Field(None, description="Additional notes")


class InvoiceCreate(InvoiceBase):
    """Schema for creating AR Invoice (always starts as DRAFT)."""
    pass


class InvoiceUpdate(BaseModel):
    """Schema for updating AR Invoice (only allowed in DRAFT status)."""
    invoice_no: Optional[str] = Field(None, min_length=1, max_length=50)
    customer_id: Optional[int] = Field(None, gt=0)
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    total_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    notes: Optional[str] = None


class InvoicePost(BaseModel):
    """Schema for posting invoice (DRAFT → POSTED transition)."""
    pass  # No fields needed, just triggers state change


class InvoiceResponse(InvoiceBase):
    """Schema for AR Invoice response."""
    id: int
    org_id: int
    status: str = Field(..., description="draft, posted, partial, paid, overdue, cancelled")
    paid_amount: Decimal = Field(..., description="Amount already paid")
    created_at: datetime
    updated_at: datetime
    
    @computed_field
    @property
    def remaining_amount(self) -> Decimal:
        """Calculate remaining unpaid balance."""
        return self.total_amount - self.paid_amount
    
    model_config = {"from_attributes": True}


class PaginatedInvoicesResponse(BaseModel):
    """Paginated response for invoices list."""
    total: int
    skip: int
    limit: int
    items: list[InvoiceResponse]


# ==================== BULK IMPORT SCHEMAS ====================

class InvoiceBulkImportItem(BaseModel):
    """Schema for single invoice in bulk import."""
    invoice_no: str = Field(..., min_length=1, max_length=50, description="Invoice number")
    customer_id: int = Field(..., gt=0, description="Customer ID")
    issue_date: date = Field(..., description="Invoice issue date")
    due_date: date = Field(..., description="Payment due date")
    total_amount: Decimal = Field(..., gt=0, decimal_places=2, description="Total invoice amount")
    notes: Optional[str] = Field(None, description="Additional notes")


class InvoiceBulkImportRequest(BaseModel):
    """Schema for bulk invoice import request."""
    invoices: list[InvoiceBulkImportItem] = Field(..., min_length=1, max_length=100, description="List of invoices to import")
    auto_post: bool = Field(False, description="Automatically post invoices after creation")


class InvoiceBulkImportResultItem(BaseModel):
    """Result for single invoice in bulk import."""
    invoice_no: str
    success: bool
    id: Optional[int] = None
    error: Optional[str] = None


class InvoiceBulkImportResponse(BaseModel):
    """Response for bulk invoice import."""
    total_submitted: int
    total_success: int
    total_failed: int
    results: list[InvoiceBulkImportResultItem]
