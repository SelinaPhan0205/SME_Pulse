"""Mô-đun Tài chính - Hóa đơn AR/AP, thanh toán, tài khoản và hóa đơn."""

from app.modules.finance.router import router as finance_router
from app.modules.finance.accounts.router import router as accounts_router
from app.modules.finance.bills.router import router as bills_router

__all__ = ["finance_router", "accounts_router", "bills_router"]
