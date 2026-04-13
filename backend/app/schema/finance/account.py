"""Schema Quản lý Tài khoản - Tài khoản Ngân hàng/Tiền mặt."""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AccountCreate(BaseModel):
    """Schema cho việc tạo tài khoản mới."""
    name: str = Field(..., min_length=1, max_length=255, description="Account name")
    type: str = Field(..., description="Account type: cash, bank")
    account_number: Optional[str] = Field(None, max_length=50, description="Account number (for bank accounts)")
    bank_name: Optional[str] = Field(None, max_length=255, description="Bank name (for bank accounts)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Tài khoản Vietcombank",
                "type": "bank",
                "account_number": "1234567890",
                "bank_name": "Vietcombank"
            }
        }


class AccountUpdate(BaseModel):
    """Schema cho việc cập nhật tài khoản (tất cả các trường là tuy chọn)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    account_number: Optional[str] = Field(None, max_length=50)
    bank_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    """Schema cho phản hồi tài khoản."""
    id: int
    name: str
    type: str
    account_number: Optional[str]
    bank_name: Optional[str]
    is_active: bool
    org_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaginatedAccountsResponse(BaseModel):
    """Phản hồi có phân trang cho danh sách tài khoản."""
    items: list[AccountResponse]
    total: int
    skip: int
    limit: int
