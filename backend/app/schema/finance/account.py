"""Account Management Schemas - Bank/Cash accounts."""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AccountCreate(BaseModel):
    """Schema for creating new account."""
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
    """Schema for updating account (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    account_number: Optional[str] = Field(None, max_length=50)
    bank_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    """Schema for account response."""
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
    """Paginated response for account list."""
    items: list[AccountResponse]
    total: int
    skip: int
    limit: int
