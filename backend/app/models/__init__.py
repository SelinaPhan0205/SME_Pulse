"""Models Package - Register all domain models for Alembic"""

# Import Base to expose metadata
from app.db.base import Base

# Import all models to register them with Base.metadata
from app.models.core import (
    Organization,
    Role,
    User,
    UserRole,
    Customer,
    Supplier,
    Account,
)

from app.models.finance import (
    ARInvoice,
    APBill,
    Payment,
    PaymentAllocation,
)

from app.models.analytics import (
    ExportJob,
    Alert,
    Setting,
)

# Export all models for easy imports
__all__ = [
    "Base",
    # Core models
    "Organization",
    "Role",
    "User",
    "UserRole",
    "Customer",
    "Supplier",
    "Account",
    # Finance models
    "ARInvoice",
    "APBill",
    "Payment",
    "PaymentAllocation",
    # Analytics models
    "ExportJob",
    "Alert",
    "Setting",
]
