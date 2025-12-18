"""Finance Domain Models: AR Invoices, AP Bills, Payments"""
from sqlalchemy import String, Integer, ForeignKey, Numeric, Date, Text, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import date
from decimal import Decimal
from app.db.base import Base, TimestampMixin, TenantMixin


class ARInvoice(Base, TimestampMixin, TenantMixin):
    """ARInvoice - Accounts Receivable invoices (sales)"""
    __tablename__ = "ar_invoices"
    __table_args__ = (
        Index("ix_ar_invoices_status_org", "status", "org_id"),
        Index("ix_ar_invoices_due_date_org", "due_date", "org_id"),
        {"schema": "finance"}
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_no: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("core.customers.id", ondelete="RESTRICT"), 
        nullable=False
    )
    
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    
    status: Mapped[str] = mapped_column(
        String(20), 
        default="draft", 
        index=True
    )  # draft, posted, paid, overdue, cancelled
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")  # type: ignore


class APBill(Base, TimestampMixin, TenantMixin):
    """APBill - Accounts Payable bills (purchases)"""
    __tablename__ = "ap_bills"
    __table_args__ = (
        Index("ix_ap_bills_status_org", "status", "org_id"),
        Index("ix_ap_bills_due_date_org", "due_date", "org_id"),
        {"schema": "finance"}
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bill_no: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("core.suppliers.id", ondelete="RESTRICT"), 
        nullable=False
    )
    
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    
    status: Mapped[str] = mapped_column(
        String(20), 
        default="unpaid", 
        index=True
    )  # unpaid, partial, paid, cancelled
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier")  # type: ignore


class Payment(Base, TimestampMixin, TenantMixin):
    """Payment - Cash/bank transactions"""
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_transaction_date_org", "transaction_date", "org_id"),
        {"schema": "finance"}
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("core.accounts.id", ondelete="RESTRICT"), 
        nullable=False
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))  # cash, transfer, vietqr
    reference_code: Mapped[Optional[str]] = mapped_column(String(100))  # Bank transaction code
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    account: Mapped["Account"] = relationship("Account")  # type: ignore
    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        "PaymentAllocation", 
        back_populates="payment",
        cascade="all, delete-orphan"
    )


class PaymentAllocation(Base, TimestampMixin, TenantMixin):
    """PaymentAllocation - Links payments to invoices/bills"""
    __tablename__ = "payment_allocations"
    __table_args__ = (
        CheckConstraint(
            '(ar_invoice_id IS NOT NULL AND ap_bill_id IS NULL) OR (ar_invoice_id IS NULL AND ap_bill_id IS NOT NULL)',
            name='check_allocation_target_exclusive'
        ),
        {"schema": "finance"}
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("finance.payments.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # One allocation links to either AR Invoice OR AP Bill (not both)
    ar_invoice_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("finance.ar_invoices.id", ondelete="RESTRICT")
    )
    ap_bill_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("finance.ap_bills.id", ondelete="RESTRICT")
    )
    
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="allocations")
    ar_invoice: Mapped[Optional["ARInvoice"]] = relationship("ARInvoice")
    ap_bill: Mapped[Optional["APBill"]] = relationship("APBill")
