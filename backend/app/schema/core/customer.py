"""Customer schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class CustomerBase(BaseModel):
    """Base schema for Customer - shared fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Customer name")
    code: Optional[str] = Field(None, max_length=50, description="Customer code (unique within org)")
    tax_code: Optional[str] = Field(None, max_length=50, description="Tax identification number")
    email: Optional[EmailStr] = Field(None, description="Customer email")
    phone: Optional[str] = Field(None, max_length=50, description="Customer phone")
    address: Optional[str] = Field(None, description="Customer address")
    credit_term: int = Field(30, ge=0, le=365, description="Credit term in days")
    is_active: bool = Field(True, description="Customer active status")


class CustomerCreate(CustomerBase):
    """Schema for creating a new Customer."""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a Customer - all fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    tax_code: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    credit_term: Optional[int] = Field(None, ge=0, le=365)
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """Schema for Customer response - includes DB fields."""
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PaginatedCustomersResponse(BaseModel):
    """Paginated response for customers list."""
    total: int
    skip: int
    limit: int
    items: list[CustomerResponse]
