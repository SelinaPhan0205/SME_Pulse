"""AP Bill (Accounts Payable) Schemas - Pydantic models for Bills CRUD."""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal


class BillCreate(BaseModel):
    """Schema for creating new AP bill."""
    bill_no: str = Field(..., min_length=1, max_length=50, description="Bill number (unique within org)")
    supplier_id: int = Field(..., gt=0, description="Supplier ID")
    issue_date: date = Field(..., description="Bill issue date")
    due_date: date = Field(..., description="Payment due date")
    total_amount: Decimal = Field(..., gt=0, description="Total bill amount")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "bill_no": "BILL-2024-001",
                "supplier_id": 1,
                "issue_date": "2024-01-15",
                "due_date": "2024-02-14",
                "total_amount": 5000000.00,
                "notes": "Hóa đơn mua hàng tháng 1"
            }
        }


class BillUpdate(BaseModel):
    """Schema for updating bill (all fields optional, only for DRAFT bills)."""
    supplier_id: Optional[int] = Field(None, gt=0)
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    total_amount: Optional[Decimal] = Field(None, gt=0)
    notes: Optional[str] = None


class BillResponse(BaseModel):
    """Schema for bill response."""
    id: int
    bill_no: str
    supplier_id: int
    issue_date: date
    due_date: date
    total_amount: Decimal
    paid_amount: Decimal
    status: str
    notes: Optional[str]
    org_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaginatedBillsResponse(BaseModel):
    """Paginated response for bill list."""
    items: list[BillResponse]
    total: int
    skip: int
    limit: int


# ==================== BULK IMPORT SCHEMAS ====================

class BillBulkImportItem(BaseModel):
    """Schema for single bill in bulk import."""
    bill_no: str = Field(..., min_length=1, max_length=50, description="Bill number")
    supplier_id: int = Field(..., gt=0, description="Supplier ID")
    issue_date: date = Field(..., description="Bill issue date")
    due_date: date = Field(..., description="Payment due date")
    total_amount: Decimal = Field(..., gt=0, description="Total bill amount")
    notes: Optional[str] = Field(None, description="Additional notes")


class BillBulkImportRequest(BaseModel):
    """Schema for bulk bill import request."""
    bills: list[BillBulkImportItem] = Field(..., min_length=1, max_length=100, description="List of bills to import")
    auto_post: bool = Field(False, description="Automatically post bills after creation")


class BillBulkImportResultItem(BaseModel):
    """Result for single bill in bulk import."""
    bill_no: str
    success: bool
    id: Optional[int] = None
    error: Optional[str] = None


class BillBulkImportResponse(BaseModel):
    """Response for bulk bill import."""
    total_submitted: int
    total_success: int
    total_failed: int
    results: list[BillBulkImportResultItem]