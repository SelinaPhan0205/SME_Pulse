"""Các schema liên quan đến người dùng."""

from typing import List, Optional
from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """Cáu trúc tải trọng JWT token."""
    sub: int = Field(..., description="User ID")
    org_id: int = Field(..., description="Organization ID for multi-tenancy")
    roles: List[str] = Field(default_factory=list, description="User roles")
    exp: Optional[int] = Field(None, description="Expiration timestamp")


class UserResponse(BaseModel):
    """Phản hồi người dùng cho endpoint /auth/me."""
    id: int
    email: str
    full_name: Optional[str] = None
    org_id: int
    status: str
    roles: List[str] = Field(..., description="User roles")
    
    class Config:
        from_attributes = True
