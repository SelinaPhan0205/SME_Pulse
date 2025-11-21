"""Core Domain Models: Identity, Users, Partners, Accounts"""
from sqlalchemy import String, Integer, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.db.base import Base, TimestampMixin, TenantMixin


class Organization(Base, TimestampMixin):
    """Organization (Tenant) - Root entity for multi-tenancy"""
    __tablename__ = "organizations"
    __table_args__ = {"schema": "core"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_code: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)


class Role(Base):
    """Role - System-wide roles (owner, accountant, cashier)"""
    __tablename__ = "roles"
    __table_args__ = {"schema": "core"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class User(Base, TimestampMixin, TenantMixin):
    """User - Application users with organization membership"""
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_org", "email", "org_id"),
        {"schema": "core"}
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")
    
    # Relationships
    roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")


class UserRole(Base, TimestampMixin, TenantMixin):
    """UserRole - Many-to-many relationship between Users and Roles"""
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "core"}
    
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("core.users.id", ondelete="CASCADE"), 
        primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("core.roles.id", ondelete="RESTRICT"), 
        primary_key=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="roles")
    role: Mapped["Role"] = relationship("Role")


class Customer(Base, TimestampMixin, TenantMixin):
    """Customer - Accounts Receivable partners"""
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_code_org", "code", "org_id"),
        {"schema": "core"}
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_code: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    credit_term: Mapped[int] = mapped_column(Integer, default=30)  # Days
    is_active: Mapped[bool] = mapped_column(default=True)


class Supplier(Base, TimestampMixin, TenantMixin):
    """Supplier - Accounts Payable partners"""
    __tablename__ = "suppliers"
    __table_args__ = (
        Index("ix_suppliers_code_org", "code", "org_id"),
        {"schema": "core"}
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_code: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    payment_term: Mapped[int] = mapped_column(Integer, default=30)  # Days
    is_active: Mapped[bool] = mapped_column(default=True)


class Account(Base, TimestampMixin, TenantMixin):
    """Account - Bank/Cash accounts for payments"""
    __tablename__ = "accounts"
    __table_args__ = {"schema": "core"}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # cash, bank
    account_number: Mapped[Optional[str]] = mapped_column(String(50))
    bank_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
