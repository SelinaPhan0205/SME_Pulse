"""User-related schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: int = Field(..., description="User ID")
    org_id: int = Field(..., description="Organization ID for multi-tenancy")
    roles: List[str] = Field(default_factory=list, description="User roles")
    exp: Optional[int] = Field(None, description="Expiration timestamp")


class UserResponse(BaseModel):
    """User response for /auth/me endpoint."""
    id: int
    email: str
    full_name: Optional[str] = None
    org_id: int
    status: str
    roles: List[str] = Field(..., description="User roles")
    
    class Config:
        from_attributes = True
