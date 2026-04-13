"""Schema Quản lý Người dùng - Các mô hình Pydantic cho CRUD Người dùng."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


class UserCreate(BaseModel):
    """Schema cho việc tạo người dùng mới."""
    email: EmailStr = Field(..., description="User email (must be unique within organization)")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    password: str = Field(..., min_length=6, max_length=100, description="User password (min 6 chars)")
    role: str = Field(..., description="User role: owner, admin, accountant, cashier")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Xác thực vai trò là một trong các giá trị cho phép."""
        allowed_roles = ['owner', 'admin', 'accountant', 'cashier']
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class UserUpdate(BaseModel):
    """Schema cho việc cập nhật người dùng (tất cả các trường là tuy chọn)."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, description="User role")
    status: Optional[str] = Field(None, description="User status: active, inactive")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Xác thực vai trò nếu được cung cấp."""
        if v is not None:
            allowed_roles = ['owner', 'admin', 'accountant', 'cashier']
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Xác thực trạng thái nếu được cung cấp."""
        if v is not None:
            allowed_statuses = ['active', 'inactive']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v


class UserResponse(BaseModel):
    """Schema cho phản hồi người dùng."""
    id: int
    email: str
    full_name: Optional[str]
    org_id: int
    status: str
    roles: List[str] = Field(..., description="User roles")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaginatedUsersResponse(BaseModel):
    """Phản hồi có phân trang cho danh sách người dùng."""
    items: List[UserResponse]
    total: int
    skip: int
    limit: int


class ResetPasswordRequest(BaseModel):
    """Schema cho việc đặt lại mật khẩu người dùng (Chỉ Quản trị viên)."""
    new_password: str = Field(..., min_length=6, max_length=100, description="New password (min 6 chars)")
