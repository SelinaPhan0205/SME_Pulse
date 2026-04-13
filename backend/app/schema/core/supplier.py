"""Schema Nhà cung cấp."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class SupplierBase(BaseModel):
    """Schema cơ bản cho Nhà cung cấp - các trường chia sẻ."""
    name: str = Field(..., min_length=1, max_length=255, description="Supplier name")
    code: Optional[str] = Field(None, max_length=50, description="Supplier code (unique within org)")
    tax_code: Optional[str] = Field(None, max_length=50, description="Tax identification number")
    email: Optional[EmailStr] = Field(None, description="Supplier email")
    phone: Optional[str] = Field(None, max_length=50, description="Supplier phone")
    address: Optional[str] = Field(None, description="Supplier address")
    payment_term: int = Field(30, ge=0, le=365, description="Payment term in days")
    is_active: bool = Field(True, description="Supplier active status")


class SupplierCreate(SupplierBase):
    """Schema cho việc tạo mới Nhà cung cấp."""
    pass


class SupplierUpdate(BaseModel):
    """Schema cho việc cập nhật Nhà cung cấp - tất cả các trường là tuy chọn."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    tax_code: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    payment_term: Optional[int] = Field(None, ge=0, le=365)
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    """Schema cho phản hồi Nhà cung cấp - bao gồm các trường CSDL."""
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PaginatedSuppliersResponse(BaseModel):
    """Phản hồi có phân trang cho danh sách nhà cung cấp."""
    total: int
    skip: int
    limit: int
    items: list[SupplierResponse]
