"""Invoice Service - Business logic for AR Invoice management."""

from datetime import date
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import ARInvoice
from app.models.core import Customer
from app.schema.finance import InvoiceCreate, InvoiceUpdate, InvoicePost


async def get_invoices(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[Sequence[ARInvoice], int]:
    """Get list of AR invoices with filtering and pagination.
    
    Args:
        db: Database session
        org_id: Organization ID from JWT
        skip: Offset for pagination
        limit: Max records to return
        status: Filter by invoice status
        customer_id: Filter by customer
        date_from: Filter by issue_date >= date_from
        date_to: Filter by issue_date <= date_to
    
    Returns:
        Tuple of (invoice list, total count)
    """
    # Build base query
    query = select(ARInvoice).where(ARInvoice.org_id == org_id)
    count_query = select(func.count()).select_from(ARInvoice).where(ARInvoice.org_id == org_id)
    
    # Apply filters
    if status:
        query = query.where(ARInvoice.status == status)
        count_query = count_query.where(ARInvoice.status == status)
    
    if customer_id:
        query = query.where(ARInvoice.customer_id == customer_id)
        count_query = count_query.where(ARInvoice.customer_id == customer_id)
    
    if date_from:
        query = query.where(ARInvoice.issue_date >= date_from)
        count_query = count_query.where(ARInvoice.issue_date >= date_from)
    
    if date_to:
        query = query.where(ARInvoice.issue_date <= date_to)
        count_query = count_query.where(ARInvoice.issue_date <= date_to)
    
    # Add pagination
    query = query.offset(skip).limit(limit).order_by(ARInvoice.issue_date.desc())
    
    # Execute queries
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    return invoices, total


async def get_invoice(
    db: AsyncSession,
    invoice_id: int,
    org_id: int,
) -> ARInvoice:
    """Get single invoice by ID.
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        org_id: Organization ID from JWT
    
    Returns:
        ARInvoice instance
    
    Raises:
        HTTPException: 404 if not found or belongs to different org
    """
    query = select(ARInvoice).where(
        ARInvoice.id == invoice_id,
        ARInvoice.org_id == org_id,
    )
    result = await db.execute(query)
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )
    
    return invoice


async def create_invoice(
    db: AsyncSession,
    schema: InvoiceCreate,
    org_id: int,
) -> ARInvoice:
    """Create new AR invoice in DRAFT status.
    
    Args:
        db: Database session
        schema: Invoice creation data
        org_id: Organization ID from JWT
    
    Returns:
        Created ARInvoice instance
    
    Raises:
        HTTPException: 400 if customer doesn't exist or belongs to different org
    """
    # Validate customer exists and belongs to org
    customer_query = select(Customer).where(
        Customer.id == schema.customer_id,
        Customer.org_id == org_id,
    )
    customer_result = await db.execute(customer_query)
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer {schema.customer_id} not found in your organization",
        )
    
    # Create invoice in DRAFT status
    invoice = ARInvoice(
        **schema.model_dump(),
        org_id=org_id,
        status="draft",
        paid_amount=0,  # Always start at 0
    )
    
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


async def update_invoice(
    db: AsyncSession,
    invoice_id: int,
    schema: InvoiceUpdate,
    org_id: int,
) -> ARInvoice:
    """Update invoice fields (only allowed in DRAFT status).
    
    Args:
        db: Database session
        invoice_id: Invoice ID to update
        schema: Fields to update
        org_id: Organization ID from JWT
    
    Returns:
        Updated ARInvoice instance
    
    Raises:
        HTTPException: 404 if not found, 400 if already posted
    """
    invoice = await get_invoice(db, invoice_id, org_id)
    
    # Only allow updates on DRAFT invoices
    if invoice.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update invoice in {invoice.status} status. Only DRAFT invoices can be modified.",
        )
    
    # If customer_id is being changed, validate it exists
    if schema.customer_id is not None and schema.customer_id != invoice.customer_id:
        customer_query = select(Customer).where(
            Customer.id == schema.customer_id,
            Customer.org_id == org_id,
        )
        customer_result = await db.execute(customer_query)
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer {schema.customer_id} not found in your organization",
            )
    
    # Update fields (exclude unset to allow partial updates)
    update_data = schema.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)
    
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


async def post_invoice(
    db: AsyncSession,
    invoice_id: int,
    org_id: int,
) -> ARInvoice:
    """Post invoice (DRAFT → POSTED transition).
    
    After posting, invoice becomes immutable (cannot be updated/deleted).
    
    Args:
        db: Database session
        invoice_id: Invoice ID to post
        org_id: Organization ID from JWT
    
    Returns:
        Posted ARInvoice instance
    
    Raises:
        HTTPException: 404 if not found, 400 if already posted or invalid amount
    """
    invoice = await get_invoice(db, invoice_id, org_id)
    
    # Validate current status
    if invoice.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice is already {invoice.status}. Only DRAFT invoices can be posted.",
        )
    
    # Validate total_amount is positive
    if invoice.total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot post invoice with zero or negative total amount",
        )
    
    # Transition to POSTED
    invoice.status = "posted"
    
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


async def delete_invoice(
    db: AsyncSession,
    invoice_id: int,
    org_id: int,
) -> None:
    """Delete invoice (only allowed in DRAFT status).
    
    Args:
        db: Database session
        invoice_id: Invoice ID to delete
        org_id: Organization ID from JWT
    
    Raises:
        HTTPException: 404 if not found, 400 if already posted
    """
    invoice = await get_invoice(db, invoice_id, org_id)
    
    # Only allow deletion of DRAFT invoices
    if invoice.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete invoice in {invoice.status} status. Only DRAFT invoices can be deleted.",
        )
    
    await db.delete(invoice)
    await db.commit()
