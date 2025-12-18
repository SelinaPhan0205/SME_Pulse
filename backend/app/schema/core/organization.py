"""Organization settings schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class OrganizationSettings(BaseModel):
    """Organization settings response."""
    id: int
    name: str = Field(..., description="Company name")
    tax_code: Optional[str] = Field(None, description="Tax identification number")
    address: Optional[str] = Field(None, description="Company address")
    is_active: bool = Field(..., description="Organization active status")
    
    class Config:
        from_attributes = True


class OrganizationSettingsUpdate(BaseModel):
    """Organization settings update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Company name")
    tax_code: Optional[str] = Field(None, max_length=50, description="Tax identification number")
    address: Optional[str] = Field(None, description="Company address")
