"""Schema Khách hàng."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class CustomerBase(BaseModel):
    """Schema cơ bản cho Khách hàng - các trường chia sẻ."""
    name: str = Field(..., min_length=1, max_length=255, description="Customer name")
    code: Optional[str] = Field(None, max_length=50, description="Customer code (unique within org)")
    tax_code: Optional[str] = Field(None, max_length=50, description="Tax identification number")
    email: Optional[EmailStr] = Field(None, description="Customer email")
    phone: Optional[str] = Field(None, max_length=50, description="Customer phone")
    address: Optional[str] = Field(None, description="Customer address")
    credit_term: int = Field(30, ge=0, le=365, description="Credit term in days")
    is_active: bool = Field(True, description="Customer active status")


class CustomerCreate(CustomerBase):
    """Schema cho việc tạo mới Khách hàng."""
    pass


class CustomerUpdate(BaseModel):
    """Schema cho việc cập nhật Khách hàng - tất cả các trường là tuy chọn."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    tax_code: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    credit_term: Optional[int] = Field(None, ge=0, le=365)
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """Schema cho phản hồi Khách hàng - bao gồm các trường CSDL."""
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PaginatedCustomersResponse(BaseModel):
    """Phản hồi có phân trang cho danh sách khách hàng."""
    total: int
    skip: int
    limit: int
    items: list[CustomerResponse]
