"""Analytics Domain Models: Export Jobs, Alerts, Settings"""
from sqlalchemy import String, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any
from app.db.base import Base, TimestampMixin, TenantMixin


class ExportJob(Base, TimestampMixin, TenantMixin):
    """ExportJob - Background export tasks (AR reports, cashflow, etc.)"""
    __tablename__ = "export_jobs"
    __table_args__ = {"schema": "analytics"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ar_report, cashflow, etc.
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, running, completed, failed
    file_url: Mapped[Optional[str]] = mapped_column(Text)
    error_log: Mapped[Optional[str]] = mapped_column(Text)
    job_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # Additional job parameters


class Alert(Base, TimestampMixin, TenantMixin):
    """Alert - System notifications for overdue invoices, low balance, etc."""
    __tablename__ = "alerts"
    __table_args__ = {"schema": "analytics"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # overdue_invoice, low_balance, etc.
    title: Mapped[Optional[str]] = mapped_column(String(255))
    message: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, error, critical
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, read, dismissed
    alert_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # Related entity IDs, etc.


class Setting(Base, TimestampMixin, TenantMixin):
    """Setting - Tenant-specific configuration (JSON key-value store)"""
    __tablename__ = "settings"
    __table_args__ = {"schema": "analytics"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
