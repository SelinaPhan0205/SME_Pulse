"""Finance Router - AR/AP Invoices and Payments."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import get_current_user
from app.models.core import User
from app.schema.finance import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoicePost,
    InvoiceResponse,
    PaginatedInvoicesResponse,
    InvoiceBulkImportRequest,
    InvoiceBulkImportResponse,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaginatedPaymentsResponse,
)
from app.modules.finance.services import invoice_service, payment_service


router = APIRouter()


# ==================== AR INVOICES ====================

@router.get("/invoices", response_model=PaginatedInvoicesResponse)
async def list_invoices(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List AR invoices with filtering and pagination.
    
    Query Parameters:
        - skip: Offset for pagination (default: 0)
        - limit: Max records to return (default: 100)
        - status: Filter by invoice status (draft, posted, partial, paid, overdue, cancelled)
        - customer_id: Filter by customer ID
        - date_from: Filter by issue_date >= date_from
        - date_to: Filter by issue_date <= date_to
    """
    invoices, total = await invoice_service.get_invoices(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        status=status,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
    )
    
    return PaginatedInvoicesResponse(
        items=[InvoiceResponse.model_validate(inv) for inv in invoices],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single invoice by ID."""
    invoice = await invoice_service.get_invoice(
        db=db,
        invoice_id=invoice_id,
        org_id=current_user.org_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new AR invoice in DRAFT status.
    
    New invoices always start with:
    - status = "draft"
    - paid_amount = 0
    """
    invoice = await invoice_service.create_invoice(
        db=db,
        schema=invoice_in,
        org_id=current_user.org_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_in: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update invoice fields (only allowed in DRAFT status).
    
    Raises:
        400: If invoice is already posted
    """
    invoice = await invoice_service.update_invoice(
        db=db,
        invoice_id=invoice_id,
        schema=invoice_in,
        org_id=current_user.org_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.post("/invoices/{invoice_id}/post", response_model=InvoiceResponse)
async def post_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Post invoice (DRAFT → POSTED transition).
    
    **RBAC:** Only Accountant, Admin, or Owner can post invoices.
    Cashiers are restricted from posting.
    
    After posting, invoice becomes immutable:
    - Cannot be updated
    - Cannot be deleted
    - Can receive payment allocations
    
    Raises:
        403: If user role is not authorized (e.g., Cashier)
        400: If invoice is already posted or has invalid amount
    """
    # RBAC Check: Only Accountant/Admin/Owner can post
    user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['accountant', 'admin', 'owner'] for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Accountant, Admin, or Owner can post invoices. Cashiers are not authorized.",
        )
    
    invoice = await invoice_service.post_invoice(
        db=db,
        invoice_id=invoice_id,
        org_id=current_user.org_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete invoice (only allowed in DRAFT status).
    
    Raises:
        400: If invoice is already posted
    """
    await invoice_service.delete_invoice(
        db=db,
        invoice_id=invoice_id,
        org_id=current_user.org_id,
    )
    return None


@router.post("/invoices/bulk-import", response_model=InvoiceBulkImportResponse)
async def bulk_import_invoices(
    import_request: InvoiceBulkImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk import invoices from Excel/CSV data.
    
    **RBAC:** Accountant, Admin, or Owner can import invoices.
    
    Request Body:
        - invoices: List of invoice objects (max 100)
        - auto_post: If True, invoices will be posted automatically after creation
    
    Returns:
        Import results with success/failure for each invoice
    
    Notes:
        - Duplicate invoice_no will be rejected
        - Invalid customer_id will cause failure
        - Partial imports are allowed (some succeed, some fail)
    """
    # RBAC Check: Only Accountant/Admin/Owner can bulk import
    user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['accountant', 'admin', 'owner'] for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Accountant, Admin, or Owner can bulk import invoices.",
        )
    
    result = await invoice_service.bulk_import_invoices(
        db=db,
        invoices_data=import_request.invoices,
        org_id=current_user.org_id,
        auto_post=import_request.auto_post,
    )
    
    return InvoiceBulkImportResponse(**result)


# ==================== PAYMENTS ====================

@router.get("/payments", response_model=PaginatedPaymentsResponse)
async def list_payments(
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_id: Optional[int] = None,
    payment_method: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List payments with pagination and filtering.
    
    Query Parameters:
        - skip: Offset for pagination (default: 0)
        - limit: Max records to return (default: 100)
        - date_from: Filter by transaction_date >= date_from
        - date_to: Filter by transaction_date <= date_to
        - account_id: Filter by account ID
        - payment_method: Filter by payment method (cash, transfer, vietqr, card)
    """
    payments, total = await payment_service.get_payments(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        payment_method=payment_method,
    )
    
    return PaginatedPaymentsResponse(
        items=[PaymentResponse.model_validate(pmt) for pmt in payments],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single payment by ID with allocations."""
    payment = await payment_service.get_payment(
        db=db,
        payment_id=payment_id,
        org_id=current_user.org_id,
    )
    return PaymentResponse.model_validate(payment)


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create payment with allocations to invoices/bills.
    
    This endpoint implements ATOMIC transaction logic:
    - Creates payment record
    - Creates allocation records
    - Updates invoice/bill paid_amount
    - Updates invoice/bill status (partial/paid)
    - All changes commit together or rollback on error
    
    Business Rules:
    - Can only allocate to POSTED invoices/bills (not DRAFT)
    - Allocation amount cannot exceed remaining balance
    - Sum of allocations cannot exceed payment amount (validated by schema)
    - Each allocation must have EITHER ar_invoice_id OR ap_bill_id (exclusive)
    
    Raises:
        400: If validation fails (account, invoice, allocation amount)
    """
    payment = await payment_service.create_payment_with_allocations(
        db=db,
        schema=payment_in,
        org_id=current_user.org_id,
    )
    return PaymentResponse.model_validate(payment)


@router.put("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_in: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update payment metadata (notes and reference_code only).
    
    IMMUTABLE FIELDS (cannot be modified after creation):
    - amount: Audit trail requires original payment amount to be locked
    - transaction_date: Timestamp must remain immutable
    - account_id: Source account cannot change (breaking FK chain)
    - allocations: Cannot modify existing allocations (create new payment or unallocate separately)
    
    ALLOWED UPDATES (metadata only):
    - notes: Add/update payment notes (e.g., reasons for delayed allocation)
    - reference_code: Add/update bank transaction code/reference
    
    Use Case:
    - Payment created but bank provides transaction code later → update reference_code
    - Payment needs notes for auditing → update notes
    
    Raises:
        404: If payment not found
        400: If attempting to update immutable fields (will be rejected in service)
    """
    payment = await payment_service.update_payment(
        db=db,
        payment_id=payment_id,
        org_id=current_user.org_id,
        schema=payment_in,
    )
    return PaymentResponse.model_validate(payment)

