"""Các mô hình miền Phân tích: Công việc xuất, Cảnh báo, Cài đặt"""
from sqlalchemy import String, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any
from app.db.base import Base, TimestampMixin, TenantMixin


class ExportJob(Base, TimestampMixin, TenantMixin):
    """ExportJob - Công việc xuất dữ liệu nền (Báo cáo AR, dòng tiền, vv)"""
    __tablename__ = "export_jobs"
    __table_args__ = {"schema": "analytics"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ar_report, cashflow, etc. (báo cáo AR, dòng tiền, vv)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, running, completed, failed (chờ xử lý, đang chạy, hoàn thành, thất bại)
    file_url: Mapped[Optional[str]] = mapped_column(Text)
    error_log: Mapped[Optional[str]] = mapped_column(Text)
    job_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # Các tham số công việc bổ sung


class Alert(Base, TimestampMixin, TenantMixin):
    """Alert - Thông báo hệ thống cho hóa đơn quá hạn, số dư thấp, vv"""
    __tablename__ = "alerts"
    __table_args__ = {"schema": "analytics"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # overdue_invoice, low_balance, etc. (hóa đơn quá hạn, số dư thấp, vv)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    message: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, error, critical (thông tin, cảnh báo, lỗi, nguy hiểm)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, read, dismissed (mới, đã đọc, đã bỏ qua)
    alert_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # IDs thực thể liên quan, vv


class Setting(Base, TimestampMixin, TenantMixin):
    """Setting - Cấu hình cụ thể của thùe (Cửa hàng JSON key-value)"""
    __tablename__ = "settings"
    __table_args__ = {"schema": "analytics"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
