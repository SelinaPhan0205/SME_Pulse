"""Login and authentication schemas."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class UserInfo(BaseModel):
    """User information in login response."""
    id: int
    email: str
    full_name: Optional[str] = None
    org_id: int
    status: str
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with JWT token."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: UserInfo = Field(..., description="User information")
    roles: List[str] = Field(..., description="User roles")


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    old_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetResponse(BaseModel):
    """Password reset response."""
    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Email where reset link was sent")
