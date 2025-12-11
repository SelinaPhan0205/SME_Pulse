"""User Management Schemas - Pydantic models for Users CRUD."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for creating new user."""
    email: EmailStr = Field(..., description="User email (must be unique within organization)")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    password: str = Field(..., min_length=6, max_length=100, description="User password (min 6 chars)")
    role: str = Field(..., description="User role: owner, admin, accountant, cashier")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of allowed values."""
        allowed_roles = ['owner', 'admin', 'accountant', 'cashier']
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user (all fields optional)."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, description="User role")
    status: Optional[str] = Field(None, description="User status: active, inactive")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate role if provided."""
        if v is not None:
            allowed_roles = ['owner', 'admin', 'accountant', 'cashier']
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status if provided."""
        if v is not None:
            allowed_statuses = ['active', 'inactive']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v


class UserResponse(BaseModel):
    """Schema for user response."""
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
    """Paginated response for user list."""
    items: List[UserResponse]
    total: int
    skip: int
    limit: int


class ResetPasswordRequest(BaseModel):
    """Schema for resetting user password (Admin only)."""
    new_password: str = Field(..., min_length=6, max_length=100, description="New password (min 6 chars)")
