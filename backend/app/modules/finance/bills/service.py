"""AP Bill Service Layer - Business Logic for Bills (mirror of AR Invoices)."""

import logging
from typing import Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import date

from app.models.finance import APBill
from app.models.core import Supplier
from app.schema.finance.bill import BillCreate, BillUpdate

logger = logging.getLogger(__name__)


async def get_bills(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[list[APBill], int]:
    """
    Get paginated list of bills for an organization.
    
    Args:
        db: Database session
        org_id: Organization ID (CRITICAL for multi-tenancy)
        skip: Number of records to skip
        limit: Max records to return
        status: Filter by status (draft, posted, partial, paid, cancelled)
        supplier_id: Filter by supplier ID
        date_from: Filter by issue_date >= date_from
        date_to: Filter by issue_date <= date_to
    
    Returns:
        Tuple of (bills list, total count)
    """
    # Build filters
    filters = [APBill.org_id == org_id]
    
    if status:
        filters.append(APBill.status == status)
    
    if supplier_id:
        filters.append(APBill.supplier_id == supplier_id)
    
    if date_from:
        filters.append(APBill.issue_date >= date_from)
    
    if date_to:
        filters.append(APBill.issue_date <= date_to)
    
    # Count total
    count_stmt = select(func.count()).select_from(APBill).where(and_(*filters))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Get paginated data
    stmt = (
        select(APBill)
        .where(and_(*filters))
        .options(selectinload(APBill.supplier))
        .order_by(APBill.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    bills = result.unique().scalars().all()
    
    logger.info(f"Retrieved {len(bills)} bills for org_id={org_id}")
    return list(bills), total


async def get_bill(
    db: AsyncSession,
    bill_id: int,
    org_id: int,
) -> APBill:
    """
    Get single bill by ID.
    
    CRITICAL: Always filter by org_id to prevent cross-tenant access.
    
    Args:
        db: Database session
        bill_id: Bill ID
        org_id: Organization ID
    
    Returns:
        APBill object with supplier loaded
    
    Raises:
        HTTPException 404: Bill not found
    """
    stmt = (
        select(APBill)
        .where(and_(APBill.id == bill_id, APBill.org_id == org_id))
        .options(selectinload(APBill.supplier))
    )
    result = await db.execute(stmt)
    bill = result.unique().scalar_one_or_none()
    
    if not bill:
        logger.warning(f"Bill {bill_id} not found for org_id={org_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found"
        )
    
    return bill


async def create_bill(
    db: AsyncSession,
    schema: BillCreate,
    org_id: int,
) -> APBill:
    """
    Create new bill in DRAFT status.
    
    Business Rules:
    - bill_no should be unique within organization
    - Supplier must exist and belong to organization
    - due_date must be >= issue_date
    - Default status is 'draft', paid_amount is 0
    
    Args:
        db: Database session
        schema: BillCreate schema
        org_id: Organization ID
    
    Returns:
        Created bill
    
    Raises:
        HTTPException 400: Validation errors (duplicate bill_no, invalid supplier, invalid dates)
    """
    # Validate bill_no uniqueness
    existing_stmt = select(APBill).where(
        and_(APBill.bill_no == schema.bill_no, APBill.org_id == org_id)
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bill number '{schema.bill_no}' already exists"
        )
    
    # Validate supplier exists
    supplier_stmt = select(Supplier).where(
        and_(Supplier.id == schema.supplier_id, Supplier.org_id == org_id)
    )
    supplier_result = await db.execute(supplier_stmt)
    if not supplier_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supplier {schema.supplier_id} not found"
        )
    
    # Validate dates
    if schema.due_date < schema.issue_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Due date must be >= issue date"
        )
    
    # Create bill
    bill = APBill(
        bill_no=schema.bill_no,
        supplier_id=schema.supplier_id,
        issue_date=schema.issue_date,
        due_date=schema.due_date,
        total_amount=schema.total_amount,
        paid_amount=0,
        status="draft",
        notes=schema.notes,
        org_id=org_id,
    )
    
    db.add(bill)
    await db.commit()
    await db.refresh(bill)
    
    # Load supplier
    await db.execute(
        select(APBill)
        .where(APBill.id == bill.id)
        .options(selectinload(APBill.supplier))
    )
    
    logger.info(f"Created bill {bill.id} ({bill.bill_no}) for org_id={org_id}")
    return bill


async def update_bill(
    db: AsyncSession,
    bill_id: int,
    schema: BillUpdate,
    org_id: int,
) -> APBill:
    """
    Update bill (only allowed in DRAFT status).
    
    Business Rules:
    - Can only update draft bills
    - Cannot change bill once posted
    
    Args:
        db: Database session
        bill_id: Bill ID to update
        schema: BillUpdate schema
        org_id: Organization ID
    
    Returns:
        Updated bill
    
    Raises:
        HTTPException 400: Bill already posted
        HTTPException 404: Bill not found
    """
    # Get bill
    bill = await get_bill(db, bill_id, org_id)
    
    # Check if bill is draft
    if bill.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update bills in draft status"
        )
    
    # Update fields
    if schema.supplier_id is not None:
        # Validate supplier exists
        supplier_stmt = select(Supplier).where(
            and_(Supplier.id == schema.supplier_id, Supplier.org_id == org_id)
        )
        supplier_result = await db.execute(supplier_stmt)
        if not supplier_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier {schema.supplier_id} not found"
            )
        bill.supplier_id = schema.supplier_id
    
    if schema.issue_date is not None:
        bill.issue_date = schema.issue_date
    
    if schema.due_date is not None:
        bill.due_date = schema.due_date
    
    if schema.total_amount is not None:
        bill.total_amount = schema.total_amount
    
    if schema.notes is not None:
        bill.notes = schema.notes
    
    # Validate dates
    if bill.due_date < bill.issue_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Due date must be >= issue date"
        )
    
    await db.commit()
    await db.refresh(bill)
    
    logger.info(f"Updated bill {bill.id}")
    return bill


async def post_bill(
    db: AsyncSession,
    bill_id: int,
    org_id: int,
) -> APBill:
    """
    Post bill (transition from DRAFT to POSTED).
    
    After posting, bill becomes immutable and can receive payment allocations.
    
    Business Rules:
    - Can only post draft bills
    - total_amount must be > 0
    
    Args:
        db: Database session
        bill_id: Bill ID
        org_id: Organization ID
    
    Returns:
        Posted bill
    
    Raises:
        HTTPException 400: Bill already posted or invalid amount
        HTTPException 404: Bill not found
    """
    # Get bill
    bill = await get_bill(db, bill_id, org_id)
    
    # Validate status
    if bill.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill already posted"
        )
    
    # Validate amount
    if bill.total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total amount must be greater than 0"
        )
    
    # Update status
    bill.status = "posted"
    
    await db.commit()
    await db.refresh(bill)
    
    logger.info(f"Posted bill {bill.id}")
    return bill


async def delete_bill(
    db: AsyncSession,
    bill_id: int,
    org_id: int,
) -> None:
    """
    Delete bill (only allowed in DRAFT status).
    
    Business Rules:
    - Can only delete draft bills
    - Set status to 'cancelled' (soft delete)
    
    Args:
        db: Database session
        bill_id: Bill ID
        org_id: Organization ID
    
    Raises:
        HTTPException 400: Bill already posted
        HTTPException 404: Bill not found
    """
    # Get bill
    bill = await get_bill(db, bill_id, org_id)
    
    # Check if bill is draft
    if bill.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete bills in draft status"
        )
    
    # Soft delete
    bill.status = "cancelled"
    
    await db.commit()
    
    logger.info(f"Deleted bill {bill.id} (soft delete)")
