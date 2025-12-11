"""Finance schemas - re-export for easy imports."""

from app.schema.finance.invoice import (
    InvoiceBase,
    InvoiceCreate,
    InvoiceUpdate,
    InvoicePost,
    InvoiceResponse,
    PaginatedInvoicesResponse,
    InvoiceBulkImportItem,
    InvoiceBulkImportRequest,
    InvoiceBulkImportResultItem,
    InvoiceBulkImportResponse,
)
from app.schema.finance.payment import (
    PaymentBase,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    AllocationItem,
    AllocationResponse,
    PaginatedPaymentsResponse,
)
from app.schema.finance.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    PaginatedAccountsResponse,
)
from app.schema.finance.bill import (
    BillCreate,
    BillUpdate,
    BillResponse,
    PaginatedBillsResponse,
    BillBulkImportItem,
    BillBulkImportRequest,
    BillBulkImportResultItem,
    BillBulkImportResponse,
)

__all__ = [
    # Invoice
    "InvoiceBase",
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoicePost",
    "InvoiceResponse",
    "PaginatedInvoicesResponse",
    "InvoiceBulkImportItem",
    "InvoiceBulkImportRequest",
    "InvoiceBulkImportResultItem",
    "InvoiceBulkImportResponse",
    # Payment
    "PaymentBase",
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
    "AllocationItem",
    "AllocationResponse",
    "PaginatedPaymentsResponse",
    # Bill
    "BillCreate",
    "BillUpdate",
    "BillResponse",
    "PaginatedBillsResponse",
    "BillBulkImportItem",
    "BillBulkImportRequest",
    "BillBulkImportResultItem",
    "BillBulkImportResponse",
    # Account
    "AccountCreate",
    "AccountUpdate",
    "AccountResponse",
    "PaginatedAccountsResponse",
]