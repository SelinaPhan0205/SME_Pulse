"""Payment Service - Business logic for payment and allocation management."""

from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import Payment, PaymentAllocation, ARInvoice, APBill
from app.models.core import Account
from app.schema.finance import PaymentCreate
from app.modules.finance.services.invoice_service import get_invoice


async def get_payments(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
) -> tuple[Sequence[Payment], int]:
    """Get list of payments with pagination.
    
    Args:
        db: Database session
        org_id: Organization ID from JWT
        skip: Offset for pagination
        limit: Max records to return
    
    Returns:
        Tuple of (payment list, total count)
    """
    # Build query with allocations eager loading
    query = (
        select(Payment)
        .where(Payment.org_id == org_id)
        .options(selectinload(Payment.allocations))
        .offset(skip)
        .limit(limit)
        .order_by(Payment.transaction_date.desc())
    )
    
    count_query = (
        select(func.count())
        .select_from(Payment)
        .where(Payment.org_id == org_id)
    )
    
    # Execute queries
    result = await db.execute(query)
    payments = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    return payments, total


async def get_payment(
    db: AsyncSession,
    payment_id: int,
    org_id: int,
) -> Payment:
    """Get single payment by ID with allocations.
    
    Args:
        db: Database session
        payment_id: Payment ID
        org_id: Organization ID from JWT
    
    Returns:
        Payment instance with allocations loaded
    
    Raises:
        HTTPException: 404 if not found or belongs to different org
    """
    query = (
        select(Payment)
        .where(Payment.id == payment_id, Payment.org_id == org_id)
        .options(selectinload(Payment.allocations))
    )
    result = await db.execute(query)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found",
        )
    
    return payment


async def create_payment_with_allocations(
    db: AsyncSession,
    schema: PaymentCreate,
    org_id: int,
) -> Payment:
    """Create payment with allocations to invoices/bills (ATOMIC transaction).
    
    This function implements ACID transaction logic:
    1. Validates account exists
    2. Creates Payment record
    3. For each allocation:
       - Validates invoice/bill exists and belongs to org
       - Validates allocated_amount doesn't exceed remaining balance
       - Creates PaymentAllocation record
       - Updates invoice/bill paid_amount
       - Updates invoice/bill status (partial/paid)
    4. Commits ALL changes atomically (all or nothing)
    
    Args:
        db: Database session
        schema: Payment creation data with allocations
        org_id: Organization ID from JWT
    
    Returns:
        Created Payment instance with allocations loaded
    
    Raises:
        HTTPException: 400 if validation fails (account, invoice, allocation amount)
    """
    try:
        # Step 1: Validate account exists and belongs to org
        account_query = select(Account).where(
            Account.id == schema.account_id,
            Account.org_id == org_id,
        )
        account_result = await db.execute(account_query)
        account = account_result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {schema.account_id} not found in your organization",
            )
        
        # Step 2: Create payment record
        payment = Payment(
            **schema.model_dump(exclude={'allocations'}),
            org_id=org_id,
        )
        db.add(payment)
        await db.flush()  # Get payment.id for allocations
        
        # Step 3: Process each allocation ATOMICALLY
        for alloc_item in schema.allocations:
            # Handle AR Invoice allocation
            if alloc_item.ar_invoice_id is not None:
                # Validate invoice exists and belongs to org
                invoice = await get_invoice(db, alloc_item.ar_invoice_id, org_id)
                
                # Validate invoice is POSTED (cannot allocate to DRAFT)
                if invoice.status == "draft":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot allocate payment to DRAFT invoice {invoice.invoice_no}. Post it first.",
                    )
                
                # Calculate remaining balance
                remaining = invoice.total_amount - invoice.paid_amount
                
                if alloc_item.allocated_amount > remaining:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Allocation amount {alloc_item.allocated_amount} exceeds "
                            f"remaining balance {remaining} for invoice {invoice.invoice_no}"
                        ),
                    )
                
                # Create allocation record
                allocation = PaymentAllocation(
                    payment_id=payment.id,
                    ar_invoice_id=alloc_item.ar_invoice_id,
                    allocated_amount=alloc_item.allocated_amount,
                    org_id=org_id,
                )
                db.add(allocation)
                
                # Update invoice paid_amount
                invoice.paid_amount += alloc_item.allocated_amount
                
                # Update invoice status based on paid amount
                if invoice.paid_amount >= invoice.total_amount:
                    invoice.status = "paid"
                else:
                    invoice.status = "partial"
            
            # Handle AP Bill allocation
            elif alloc_item.ap_bill_id is not None:
                # Query AP bill
                bill_query = select(APBill).where(
                    APBill.id == alloc_item.ap_bill_id,
                    APBill.org_id == org_id,
                )
                bill_result = await db.execute(bill_query)
                bill = bill_result.scalar_one_or_none()
                
                if not bill:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"AP Bill {alloc_item.ap_bill_id} not found in your organization",
                    )
                
                # Validate bill is POSTED
                if bill.status == "draft":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot allocate payment to DRAFT bill {bill.bill_no}. Post it first.",
                    )
                
                # Calculate remaining balance
                remaining = bill.total_amount - bill.paid_amount
                
                if alloc_item.allocated_amount > remaining:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Allocation amount {alloc_item.allocated_amount} exceeds "
                            f"remaining balance {remaining} for bill {bill.bill_no}"
                        ),
                    )
                
                # Create allocation record
                allocation = PaymentAllocation(
                    payment_id=payment.id,
                    ap_bill_id=alloc_item.ap_bill_id,
                    allocated_amount=alloc_item.allocated_amount,
                    org_id=org_id,
                )
                db.add(allocation)
                
                # Update bill paid_amount
                bill.paid_amount += alloc_item.allocated_amount
                
                # Update bill status
                if bill.paid_amount >= bill.total_amount:
                    bill.status = "paid"
                else:
                    bill.status = "partial"
        
        # Step 4: Commit ALL changes atomically
        await db.commit()
        await db.refresh(payment)
        
        # Load allocations relationship
        await db.refresh(payment, attribute_names=['allocations'])
        
        return payment
    
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        await db.rollback()
        raise
    except Exception as e:
        # Rollback on any other error
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}",
        )
