"""Schema lõi - tái xuất cho nhập khẩu dễ dàng."""

from app.schema.core.customer import (
    CustomerBase,
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    PaginatedCustomersResponse,
)
from app.schema.core.supplier import (
    SupplierBase,
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    PaginatedSuppliersResponse,
)

__all__ = [
    # Customer
    "CustomerBase",
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "PaginatedCustomersResponse",
    # Supplier
    "SupplierBase",
    "SupplierCreate",
    "SupplierUpdate",
    "SupplierResponse",
    "PaginatedSuppliersResponse",
]
