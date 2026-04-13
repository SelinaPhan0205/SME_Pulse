"""SQLAlchemy - Các lớp cơ sở và Mixin tái sử dụng"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Lớp cơ sở cho tất cả các SQLAlchemy models"""
    __abstract__ = True
    
    def dict(self) -> dict[str, Any]:
        """Chuyển đổi instance model thành dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TimestampMixin:
    """Mixin để tự động theo dõi thời gian tạo/cập nhật"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TenantMixin:
    """Mixin để hỗ trợ đa thuê (multi-tenancy)"""
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
