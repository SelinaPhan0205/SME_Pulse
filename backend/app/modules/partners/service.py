"""Service layer for Customers and Suppliers - Business Logic with Multi-tenancy."""

import logging
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.core import Customer, Supplier
from app.schema.core import (
    CustomerCreate,
    CustomerUpdate,
    SupplierCreate,
    SupplierUpdate,
)

logger = logging.getLogger(__name__)


# ============================================================
# CUSTOMER SERVICES
# ============================================================

async def get_customers(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> tuple[list[Customer], int]:
    """
    Get paginated list of customers for an organization.
    
    Args:
        db: Database session
        org_id: Organization ID (CRITICAL for multi-tenancy)
        skip: Number of records to skip
        limit: Max records to return
        is_active: Filter by active status (optional)
    
    Returns:
        Tuple of (customers list, total count)
    """
    # Build base query with multi-tenant filter
    base_filter = Customer.org_id == org_id
    if is_active is not None:
        base_filter = and_(base_filter, Customer.is_active == is_active)
    
    # Count total
    count_stmt = select(func.count()).select_from(Customer).where(base_filter)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Get paginated data
    stmt = (
        select(Customer)
        .where(base_filter)
        .order_by(Customer.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    customers = result.scalars().all()
    
    logger.info(f"Retrieved {len(customers)} customers for org_id={org_id}")
    return list(customers), total


async def get_customer(
    db: AsyncSession,
    customer_id: int,
    org_id: int,
) -> Customer:
    """
    Get single customer by ID.
    
    CRITICAL: Always filter by org_id to prevent cross-tenant access.
    
    Args:
        db: Database session
        customer_id: Customer ID
        org_id: Organization ID
    
    Returns:
        Customer object
    
    Raises:
        HTTPException 404: Customer not found
    """
    stmt = select(Customer).where(
        and_(
            Customer.id == customer_id,
            Customer.org_id == org_id  # Multi-tenancy protection
        )
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()
    
    if not customer:
        logger.warning(f"Customer {customer_id} not found for org_id={org_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    return customer


async def create_customer(
    db: AsyncSession,
    schema: CustomerCreate,
    org_id: int,
) -> Customer:
    """
    Create new customer.
    
    Business Rules:
    - Customer code must be unique within organization (if provided)
    - org_id is INJECTED from current_user, NOT from request body
    
    Args:
        db: Database session
        schema: Customer creation data
        org_id: Organization ID (injected from auth)
    
    Returns:
        Created customer
    
    Raises:
        HTTPException 400: Duplicate customer code
    """
    # Check for duplicate code within organization
    if schema.code:
        stmt = select(Customer).where(
            and_(
                Customer.code == schema.code,
                Customer.org_id == org_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(
                f"Duplicate customer code '{schema.code}' for org_id={org_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer with code '{schema.code}' already exists"
            )
    
    # Create customer - inject org_id
    customer = Customer(
        **schema.model_dump(),
        org_id=org_id  # CRITICAL: Inject from auth, not from request
    )
    
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    
    logger.info(f"Created customer {customer.id} for org_id={org_id}")
    return customer


async def update_customer(
    db: AsyncSession,
    customer_id: int,
    schema: CustomerUpdate,
    org_id: int,
) -> Customer:
    """
    Update existing customer.
    
    Business Rules:
    - Customer must belong to current organization
    - Code must be unique within organization (if changed)
    
    Args:
        db: Database session
        customer_id: Customer ID to update
        schema: Update data (partial)
        org_id: Organization ID
    
    Returns:
        Updated customer
    
    Raises:
        HTTPException 404: Customer not found
        HTTPException 400: Duplicate code
    """
    # Get existing customer (with multi-tenant check)
    customer = await get_customer(db, customer_id, org_id)
    
    # Check for duplicate code if code is being updated
    update_data = schema.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] != customer.code:
        stmt = select(Customer).where(
            and_(
                Customer.code == update_data["code"],
                Customer.org_id == org_id,
                Customer.id != customer_id  # Exclude current customer
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer with code '{update_data['code']}' already exists"
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    await db.commit()
    await db.refresh(customer)
    
    logger.info(f"Updated customer {customer_id} for org_id={org_id}")
    return customer


async def delete_customer(
    db: AsyncSession,
    customer_id: int,
    org_id: int,
) -> None:
    """
    Delete customer (soft delete by setting is_active=False).
    
    Args:
        db: Database session
        customer_id: Customer ID
        org_id: Organization ID
    
    Raises:
        HTTPException 404: Customer not found
    """
    customer = await get_customer(db, customer_id, org_id)
    
    # Soft delete
    customer.is_active = False
    await db.commit()
    
    logger.info(f"Deleted (soft) customer {customer_id} for org_id={org_id}")


# ============================================================
# SUPPLIER SERVICES
# ============================================================

async def get_suppliers(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> tuple[list[Supplier], int]:
    """
    Get paginated list of suppliers for an organization.
    
    Args:
        db: Database session
        org_id: Organization ID (CRITICAL for multi-tenancy)
        skip: Number of records to skip
        limit: Max records to return
        is_active: Filter by active status (optional)
    
    Returns:
        Tuple of (suppliers list, total count)
    """
    # Build base query with multi-tenant filter
    base_filter = Supplier.org_id == org_id
    if is_active is not None:
        base_filter = and_(base_filter, Supplier.is_active == is_active)
    
    # Count total
    count_stmt = select(func.count()).select_from(Supplier).where(base_filter)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Get paginated data
    stmt = (
        select(Supplier)
        .where(base_filter)
        .order_by(Supplier.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    suppliers = result.scalars().all()
    
    logger.info(f"Retrieved {len(suppliers)} suppliers for org_id={org_id}")
    return list(suppliers), total


async def get_supplier(
    db: AsyncSession,
    supplier_id: int,
    org_id: int,
) -> Supplier:
    """
    Get single supplier by ID.
    
    CRITICAL: Always filter by org_id to prevent cross-tenant access.
    
    Args:
        db: Database session
        supplier_id: Supplier ID
        org_id: Organization ID
    
    Returns:
        Supplier object
    
    Raises:
        HTTPException 404: Supplier not found
    """
    stmt = select(Supplier).where(
        and_(
            Supplier.id == supplier_id,
            Supplier.org_id == org_id  # Multi-tenancy protection
        )
    )
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        logger.warning(f"Supplier {supplier_id} not found for org_id={org_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with ID {supplier_id} not found"
        )
    
    return supplier


async def create_supplier(
    db: AsyncSession,
    schema: SupplierCreate,
    org_id: int,
) -> Supplier:
    """
    Create new supplier.
    
    Business Rules:
    - Supplier code must be unique within organization (if provided)
    - org_id is INJECTED from current_user, NOT from request body
    
    Args:
        db: Database session
        schema: Supplier creation data
        org_id: Organization ID (injected from auth)
    
    Returns:
        Created supplier
    
    Raises:
        HTTPException 400: Duplicate supplier code
    """
    # Check for duplicate code within organization
    if schema.code:
        stmt = select(Supplier).where(
            and_(
                Supplier.code == schema.code,
                Supplier.org_id == org_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(
                f"Duplicate supplier code '{schema.code}' for org_id={org_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with code '{schema.code}' already exists"
            )
    
    # Create supplier - inject org_id
    supplier = Supplier(
        **schema.model_dump(),
        org_id=org_id  # CRITICAL: Inject from auth, not from request
    )
    
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    
    logger.info(f"Created supplier {supplier.id} for org_id={org_id}")
    return supplier


async def update_supplier(
    db: AsyncSession,
    supplier_id: int,
    schema: SupplierUpdate,
    org_id: int,
) -> Supplier:
    """
    Update existing supplier.
    
    Business Rules:
    - Supplier must belong to current organization
    - Code must be unique within organization (if changed)
    
    Args:
        db: Database session
        supplier_id: Supplier ID to update
        schema: Update data (partial)
        org_id: Organization ID
    
    Returns:
        Updated supplier
    
    Raises:
        HTTPException 404: Supplier not found
        HTTPException 400: Duplicate code
    """
    # Get existing supplier (with multi-tenant check)
    supplier = await get_supplier(db, supplier_id, org_id)
    
    # Check for duplicate code if code is being updated
    update_data = schema.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] != supplier.code:
        stmt = select(Supplier).where(
            and_(
                Supplier.code == update_data["code"],
                Supplier.org_id == org_id,
                Supplier.id != supplier_id  # Exclude current supplier
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with code '{update_data['code']}' already exists"
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    await db.commit()
    await db.refresh(supplier)
    
    logger.info(f"Updated supplier {supplier_id} for org_id={org_id}")
    return supplier


async def delete_supplier(
    db: AsyncSession,
    supplier_id: int,
    org_id: int,
) -> None:
    """
    Delete supplier (soft delete by setting is_active=False).
    
    Args:
        db: Database session
        supplier_id: Supplier ID
        org_id: Organization ID
    
    Raises:
        HTTPException 404: Supplier not found
    """
    supplier = await get_supplier(db, supplier_id, org_id)
    
    # Soft delete
    supplier.is_active = False
    await db.commit()
    
    logger.info(f"Deleted (soft) supplier {supplier_id} for org_id={org_id}")
