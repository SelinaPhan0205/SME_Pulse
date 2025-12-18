"""Supplier schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class SupplierBase(BaseModel):
    """Base schema for Supplier - shared fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Supplier name")
    code: Optional[str] = Field(None, max_length=50, description="Supplier code (unique within org)")
    tax_code: Optional[str] = Field(None, max_length=50, description="Tax identification number")
    email: Optional[EmailStr] = Field(None, description="Supplier email")
    phone: Optional[str] = Field(None, max_length=50, description="Supplier phone")
    address: Optional[str] = Field(None, description="Supplier address")
    payment_term: int = Field(30, ge=0, le=365, description="Payment term in days")
    is_active: bool = Field(True, description="Supplier active status")


class SupplierCreate(SupplierBase):
    """Schema for creating a new Supplier."""
    pass


class SupplierUpdate(BaseModel):
    """Schema for updating a Supplier - all fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    tax_code: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    payment_term: Optional[int] = Field(None, ge=0, le=365)
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    """Schema for Supplier response - includes DB fields."""
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PaginatedSuppliersResponse(BaseModel):
    """Paginated response for suppliers list."""
    total: int
    skip: int
    limit: int
    items: list[SupplierResponse]
