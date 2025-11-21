"""FastAPI routers for Customers and Suppliers - REST API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.core import User
from app.modules.auth.dependencies import get_current_user
from app.modules.partners import service
from app.schema.core import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    PaginatedCustomersResponse,
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    PaginatedSuppliersResponse,
)

logger = logging.getLogger(__name__)


# ============================================================
# CUSTOMERS ROUTER
# ============================================================

customers_router = APIRouter(prefix="/customers", tags=["Customers"])


@customers_router.get(
    "/",
    response_model=PaginatedCustomersResponse,
    summary="List customers",
    description="Get paginated list of customers for current organization"
)
async def list_customers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all customers for current organization.
    
    **Multi-tenancy:** Automatically filters by current user's org_id.
    
    Query Parameters:
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 100, max: 500)
    - is_active: Filter active/inactive (optional)
    
    Returns:
    - Paginated list of customers with total count
    """
    customers, total = await service.get_customers(
        db=db,
        org_id=current_user.org_id,  # Multi-tenancy filter
        skip=skip,
        limit=limit,
        is_active=is_active,
    )
    
    return PaginatedCustomersResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=customers,
    )


@customers_router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer by ID",
    description="Retrieve single customer details"
)
async def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get customer by ID.
    
    **Multi-tenancy:** Only returns customer if it belongs to current user's organization.
    
    Path Parameters:
    - customer_id: Customer ID
    
    Raises:
    - 404: Customer not found or doesn't belong to current organization
    """
    customer = await service.get_customer(
        db=db,
        customer_id=customer_id,
        org_id=current_user.org_id,  # Multi-tenancy protection
    )
    return customer


@customers_router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer",
    description="Create new customer for current organization"
)
async def create_customer(
    schema: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new customer.
    
    **Multi-tenancy:** Customer is automatically assigned to current user's organization.
    
    **Business Rules:**
    - Customer code must be unique within organization (if provided)
    - org_id is injected from authentication, NOT from request body
    
    Request Body:
    - name: Customer name (required)
    - code: Unique code within org (optional)
    - tax_code, email, phone, address: Contact info (optional)
    - credit_term: Days (default: 30)
    - is_active: Active status (default: true)
    
    Raises:
    - 400: Duplicate customer code
    """
    customer = await service.create_customer(
        db=db,
        schema=schema,
        org_id=current_user.org_id,  # Inject org_id from auth
    )
    return customer


@customers_router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer",
    description="Update existing customer"
)
async def update_customer(
    customer_id: int,
    schema: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update customer.
    
    **Multi-tenancy:** Only allows updating customer if it belongs to current user's organization.
    
    **Business Rules:**
    - All fields are optional (partial update)
    - Code must remain unique within organization (if changed)
    
    Path Parameters:
    - customer_id: Customer ID to update
    
    Request Body:
    - Any CustomerUpdate fields (all optional)
    
    Raises:
    - 404: Customer not found or doesn't belong to current organization
    - 400: Duplicate customer code
    """
    customer = await service.update_customer(
        db=db,
        customer_id=customer_id,
        schema=schema,
        org_id=current_user.org_id,  # Multi-tenancy protection
    )
    return customer


@customers_router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer",
    description="Soft delete customer (set is_active=False)"
)
async def delete_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete customer (soft delete).
    
    **Multi-tenancy:** Only allows deleting customer if it belongs to current user's organization.
    
    **Note:** This is a soft delete - sets is_active=False instead of removing from database.
    
    Path Parameters:
    - customer_id: Customer ID to delete
    
    Raises:
    - 404: Customer not found or doesn't belong to current organization
    """
    await service.delete_customer(
        db=db,
        customer_id=customer_id,
        org_id=current_user.org_id,  # Multi-tenancy protection
    )
    return None


# ============================================================
# SUPPLIERS ROUTER
# ============================================================

suppliers_router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@suppliers_router.get(
    "/",
    response_model=PaginatedSuppliersResponse,
    summary="List suppliers",
    description="Get paginated list of suppliers for current organization"
)
async def list_suppliers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all suppliers for current organization.
    
    **Multi-tenancy:** Automatically filters by current user's org_id.
    
    Query Parameters:
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 100, max: 500)
    - is_active: Filter active/inactive (optional)
    
    Returns:
    - Paginated list of suppliers with total count
    """
    suppliers, total = await service.get_suppliers(
        db=db,
        org_id=current_user.org_id,  # Multi-tenancy filter
        skip=skip,
        limit=limit,
        is_active=is_active,
    )
    
    return PaginatedSuppliersResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=suppliers,
    )


@suppliers_router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Get supplier by ID",
    description="Retrieve single supplier details"
)
async def get_supplier(
    supplier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get supplier by ID.
    
    **Multi-tenancy:** Only returns supplier if it belongs to current user's organization.
    
    Path Parameters:
    - supplier_id: Supplier ID
    
    Raises:
    - 404: Supplier not found or doesn't belong to current organization
    """
    supplier = await service.get_supplier(
        db=db,
        supplier_id=supplier_id,
        org_id=current_user.org_id,  # Multi-tenancy protection
    )
    return supplier


@suppliers_router.post(
    "/",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create supplier",
    description="Create new supplier for current organization"
)
async def create_supplier(
    schema: SupplierCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new supplier.
    
    **Multi-tenancy:** Supplier is automatically assigned to current user's organization.
    
    **Business Rules:**
    - Supplier code must be unique within organization (if provided)
    - org_id is injected from authentication, NOT from request body
    
    Request Body:
    - name: Supplier name (required)
    - code: Unique code within org (optional)
    - tax_code, email, phone, address: Contact info (optional)
    - payment_term: Days (default: 30)
    - is_active: Active status (default: true)
    
    Raises:
    - 400: Duplicate supplier code
    """
    supplier = await service.create_supplier(
        db=db,
        schema=schema,
        org_id=current_user.org_id,  # Inject org_id from auth
    )
    return supplier


@suppliers_router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Update supplier",
    description="Update existing supplier"
)
async def update_supplier(
    supplier_id: int,
    schema: SupplierUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update supplier.
    
    **Multi-tenancy:** Only allows updating supplier if it belongs to current user's organization.
    
    **Business Rules:**
    - All fields are optional (partial update)
    - Code must remain unique within organization (if changed)
    
    Path Parameters:
    - supplier_id: Supplier ID to update
    
    Request Body:
    - Any SupplierUpdate fields (all optional)
    
    Raises:
    - 404: Supplier not found or doesn't belong to current organization
    - 400: Duplicate supplier code
    """
    supplier = await service.update_supplier(
        db=db,
        supplier_id=supplier_id,
        schema=schema,
        org_id=current_user.org_id,  # Multi-tenancy protection
    )
    return supplier


@suppliers_router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete supplier",
    description="Soft delete supplier (set is_active=False)"
)
async def delete_supplier(
    supplier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete supplier (soft delete).
    
    **Multi-tenancy:** Only allows deleting supplier if it belongs to current user's organization.
    
    **Note:** This is a soft delete - sets is_active=False instead of removing from database.
    
    Path Parameters:
    - supplier_id: Supplier ID to delete
    
    Raises:
    - 404: Supplier not found or doesn't belong to current organization
    """
    await service.delete_supplier(
        db=db,
        supplier_id=supplier_id,
        org_id=current_user.org_id,  # Multi-tenancy protection
    )
    return None
