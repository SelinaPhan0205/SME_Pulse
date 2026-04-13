"""Schema Thanh toán và Phân bổ Thanh toán."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AllocationItem(BaseModel):
    """Phản bổ đơn lẻ: hóa đơn/hợp đồng nào cần thanh toán và số tiền bao nhiêu."""
    ar_invoice_id: Optional[int] = Field(None, description="AR Invoice ID to allocate to")
    ap_bill_id: Optional[int] = Field(None, description="AP Bill ID to allocate to")
    allocated_amount: Decimal = Field(..., gt=0, decimal_places=2, description="Amount to allocate")
    notes: Optional[str] = Field(None, description="Allocation notes")
    
    @field_validator('ar_invoice_id', 'ap_bill_id')
    @classmethod
    def validate_exclusive_target(cls, v, info):
        """\u0110ảm bảo lựa chọn một Hóa đơn AR HOĂC Hợp đồng AP, không phải cả."""
        values = info.data
        ar_id = values.get('ar_invoice_id')
        ap_id = values.get('ap_bill_id')
        
        # Sau khi cả hai trường được đặt, kiểm tra tính độc quyền
        if info.field_name == 'ap_bill_id':
            if (ar_id is None and ap_id is None) or (ar_id is not None and ap_id is not None):
                raise ValueError('Must allocate to either AR Invoice OR AP Bill, not both or neither')
        return v


class PaymentBase(BaseModel):
    """Schema cơ bản cho Thanh toán."""
    account_id: int = Field(..., gt=0, description="Account ID (bank/cash)")
    transaction_date: date = Field(..., description="Transaction date")
    amount: Decimal = Field(..., decimal_places=2, description="Total payment amount")
    payment_method: Optional[str] = Field(None, max_length=50, description="cash, transfer, vietqr")
    reference_code: Optional[str] = Field(None, max_length=100, description="Bank transaction code")
    notes: Optional[str] = Field(None, description="Payment notes")


class PaymentCreate(PaymentBase):
    """Schema cho việc tạo Thanh toán VĐI PHÂN BỔ (ATOMIC)."""
    allocations: list[AllocationItem] = Field(default=[], description="List of invoice/bill allocations (optional)")
    
    @field_validator('allocations')
    @classmethod
    def validate_allocation_sum(cls, v, info):
        """\u0110ảm bảo tổng phân bổ <= số tiền thanh toán."""
        values = info.data
        payment_amount = values.get('amount')
        
        if payment_amount and v:
            total_allocated = sum(item.allocated_amount for item in v)
            if total_allocated > payment_amount:
                raise ValueError(
                    f'Total allocated ({total_allocated}) exceeds payment amount ({payment_amount})'
                )
        return v


class PaymentUpdate(BaseModel):
    """Schema cho việc cập nhật Thanh toán (các trường hạn chế sau khi tạo)."""
    notes: Optional[str] = None
    reference_code: Optional[str] = Field(None, max_length=100)


class AllocationResponse(BaseModel):
    """Schema cho phản hồi Phân bổ Thanh toán."""
    id: int
    payment_id: int
    ar_invoice_id: Optional[int]
    ap_bill_id: Optional[int]
    allocated_amount: Decimal
    notes: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class PaymentResponse(PaymentBase):
    """Schema cho phản hồi Thanh toán."""
    id: int
    org_id: int
    allocations: list[AllocationResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PaginatedPaymentsResponse(BaseModel):
    """Phản hồi có phân trang cho danh sách thanh toán."""
    total: int
    skip: int
    limit: int
    items: list[PaymentResponse]
