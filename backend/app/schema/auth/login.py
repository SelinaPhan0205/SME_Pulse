"""Schema đăng nhập và xác thực."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema yêu cầu đăng nhập."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class UserInfo(BaseModel):
    """Thông tin người dùng trong phản hồi đăng nhập."""
    id: int
    email: str
    full_name: Optional[str] = None
    org_id: int
    status: str
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Phản hồi đăng nhập có JWT token."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: UserInfo = Field(..., description="User information")
    roles: List[str] = Field(..., description="User roles")


class ChangePasswordRequest(BaseModel):
    """Schema yêu cầu đổi mật khẩu."""
    old_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")


class ForgotPasswordRequest(BaseModel):
    """Schema yêu cầu quên mật khẩu."""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetResponse(BaseModel):
    """Phản hồi đặt lại mật khẩu."""
    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Email where reset link was sent")
