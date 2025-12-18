# PHASE 5: Complete Authentication Implementation Guide

**Date:** November 20, 2025  
**Project:** SME Pulse Backend  
**Purpose:** Comprehensive guide for implementing authentication system from Phase 1 to Phase 4

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Phase 1: Database Setup & Seed Data](#phase-1-database-setup--seed-data)
3. [Phase 2: Authentication Implementation](#phase-2-authentication-implementation)
4. [Phase 3: Security Middleware & Exception Handling](#phase-3-security-middleware--exception-handling)
5. [Phase 4: Testing & Verification](#phase-4-testing--verification)
6. [Troubleshooting](#troubleshooting)

---

## Overview

This guide provides step-by-step instructions to build a production-ready authentication system with:
- ✅ User authentication with JWT tokens
- ✅ Role-based authorization
- ✅ Multi-tenancy support
- ✅ Rate limiting (brute force protection)
- ✅ Structured logging & request tracking
- ✅ Security headers on all responses
- ✅ Comprehensive error handling

**Time Estimate:** 2-3 hours  
**Prerequisites:** Docker, PostgreSQL, Python 3.11+, FastAPI knowledge

---

# PHASE 1: Database Setup & Seed Data

## Step 1.1: Database Schema & Migrations

### Prerequisites Check
```bash
# Verify backend is running
docker compose ps backend

# Expected: Container should be healthy
```

### Create Database Schema
```bash
# Run Alembic migrations
docker exec -it sme-backend alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade db10dff7c201, create initial schema
# Migration successful!
```

### Verify Schema Created
```bash
# Check database tables
docker exec -it postgres_application_db psql -U postgres -d sme_pulse_oltp -c "\dt"

# Expected tables:
# core.users, core.roles, core.user_roles
# core.organizations
# finance.customers, finance.suppliers
# finance.accounts
# ... (14 tables total across 3 schemas)
```

---

## Step 1.2: Create Seed Data Structure

### Create Seed Directory
```bash
# Navigate to backend
cd backend

# Create seed structure
mkdir -p app/db/seeds
touch app/db/seeds/__init__.py
touch app/db/seeds/seed_roles.py
touch app/db/seeds/seed_organizations.py
touch app/db/seeds/seed_users.py
touch app/db/seeds/seed_customers_suppliers.py
touch app/db/seeds/seed_accounts.py
touch app/db/seeds/run_all.py
```

### Seed File 1: Roles
**File:** `app/db/seeds/seed_roles.py`
```python
"""Seed data for roles."""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Role
from app.db.session import get_db


async def seed_roles(db: AsyncSession):
    """Create default roles."""
    
    roles_data = [
        {"code": "owner", "name": "Owner", "description": "Business owner with full access"},
        {"code": "admin", "name": "Administrator", "description": "System administrator"},
        {"code": "accountant", "name": "Accountant", "description": "Financial operations"},
        {"code": "cashier", "name": "Cashier", "description": "Cash management"},
    ]
    
    for role_data in roles_data:
        # Check if exists
        stmt = select(Role).where(Role.code == role_data["code"])
        existing = await db.scalar(stmt)
        
        if not existing:
            role = Role(**role_data)
            db.add(role)
            print(f"  Created role: {role.code}")
        else:
            print(f"  Role already exists: {role_data['code']}")
    
    await db.commit()
    print("Roles seed completed!")
```

### Seed File 2: Organizations
**File:** `app/db/seeds/seed_organizations.py`
```python
"""Seed data for organizations."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization


async def seed_organizations(db: AsyncSession):
    """Create default organization."""
    
    # Check if exists
    stmt = select(Organization).where(Organization.tax_code == "1234567890")
    existing = await db.scalar(stmt)
    
    if existing:
        print(f"  Organization already exists: {existing.name}")
        return existing
    
    org = Organization(
        name="SME Demo Company",
        tax_code="1234567890",
        address="123 Business Street",
        phone="0123456789",
        email="contact@sme.com",
    )
    db.add(org)
    await db.commit()
    print(f"  Created organization: {org.name}")
    
    return org
```

### Seed File 3: Users
**File:** `app/db/seeds/seed_users.py`
```python
"""Seed data for users."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import User, UserRole
from app.core.security import get_password_hash


async def seed_users(db: AsyncSession, org_id: int, admin_role_id: int, owner_role_id: int):
    """Create default users."""
    
    # Check if exists
    stmt = select(User).where(User.email == "admin@sme.com")
    existing = await db.scalar(stmt)
    
    if existing:
        print(f"  User already exists: admin@sme.com")
        return existing
    
    # Create admin user
    user = User(
        email="admin@sme.com",
        password_hash=get_password_hash("123456"),  # Will be hashed with bcrypt
        full_name="Administrator",
        org_id=org_id,
        status="active",
    )
    db.add(user)
    await db.flush()  # Get user.id
    
    # Assign roles
    user_role_1 = UserRole(user_id=user.id, role_id=owner_role_id)
    user_role_2 = UserRole(user_id=user.id, role_id=admin_role_id)
    db.add(user_role_1)
    db.add(user_role_2)
    
    await db.commit()
    print(f"  Created user: admin@sme.com with roles: owner, admin")
    
    return user
```

### Seed File 4: Customers & Suppliers
**File:** `app/db/seeds/seed_customers_suppliers.py`
```python
"""Seed data for customers and suppliers."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Customer, Supplier


async def seed_customers_suppliers(db: AsyncSession, org_id: int):
    """Create default customers and suppliers."""
    
    # Customers
    customers_data = [
        {"name": "Tech Corp", "tax_code": "C001", "contact_person": "John Doe"},
        {"name": "Retail Ltd", "tax_code": "C002", "contact_person": "Jane Smith"},
    ]
    
    for cust_data in customers_data:
        stmt = select(Customer).where(Customer.tax_code == cust_data["tax_code"])
        existing = await db.scalar(stmt)
        
        if not existing:
            customer = Customer(
                org_id=org_id,
                name=cust_data["name"],
                tax_code=cust_data["tax_code"],
                contact_person=cust_data["contact_person"],
                status="active",
            )
            db.add(customer)
            print(f"  Created customer: {cust_data['name']}")
    
    # Suppliers
    suppliers_data = [
        {"name": "Supply Co", "tax_code": "S001", "contact_person": "Bob Wilson"},
        {"name": "Material Inc", "tax_code": "S002", "contact_person": "Alice Brown"},
    ]
    
    for sup_data in suppliers_data:
        stmt = select(Supplier).where(Supplier.tax_code == sup_data["tax_code"])
        existing = await db.scalar(stmt)
        
        if not existing:
            supplier = Supplier(
                org_id=org_id,
                name=sup_data["name"],
                tax_code=sup_data["tax_code"],
                contact_person=sup_data["contact_person"],
                status="active",
            )
            db.add(supplier)
            print(f"  Created supplier: {sup_data['name']}")
    
    await db.commit()
    print("Customers & Suppliers seed completed!")
```

### Seed File 5: Accounts
**File:** `app/db/seeds/seed_accounts.py`
```python
"""Seed data for accounts."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Account


async def seed_accounts(db: AsyncSession, org_id: int):
    """Create default accounts."""
    
    accounts_data = [
        {
            "code": "1001",
            "name": "Cash on Hand",
            "account_type": "asset",
            "status": "active",
        },
        {
            "code": "1002",
            "name": "Bank Account",
            "account_type": "asset",
            "status": "active",
        },
    ]
    
    for acc_data in accounts_data:
        stmt = select(Account).where(
            Account.org_id == org_id,
            Account.code == acc_data["code"]
        )
        existing = await db.scalar(stmt)
        
        if not existing:
            account = Account(
                org_id=org_id,
                code=acc_data["code"],
                name=acc_data["name"],
                account_type=acc_data["account_type"],
                status=acc_data["status"],
            )
            db.add(account)
            print(f"  Created account: {acc_data['name']} ({acc_data['code']})")
    
    await db.commit()
    print("Accounts seed completed!")
```

### Seed Orchestrator
**File:** `app/db/seeds/run_all.py`
```python
"""Master seed runner - executes all seeds in correct order."""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.core import Organization, Role

# Import all seed modules
from .seed_roles import seed_roles
from .seed_organizations import seed_organizations
from .seed_users import seed_users
from .seed_customers_suppliers import seed_customers_suppliers
from .seed_accounts import seed_accounts


async def run_all_seeds():
    """Run all seeds in transaction."""
    async for db in get_db():
        try:
            print("\n" + "=" * 70)
            print("STARTING SEED DATA INITIALIZATION")
            print("=" * 70 + "\n")
            
            # 1. Seed Roles (required for users)
            print("[1/5] Seeding Roles...")
            await seed_roles(db)
            
            # 2. Seed Organizations (required for users & other data)
            print("\n[2/5] Seeding Organizations...")
            org = await seed_organizations(db)
            
            # 3. Get role IDs (required for users)
            print("\n[3/5] Fetching role IDs...")
            owner_role = await db.scalar(select(Role).where(Role.code == "owner"))
            admin_role = await db.scalar(select(Role).where(Role.code == "admin"))
            
            # 4. Seed Users (requires org_id and role_ids)
            print("[4/5] Seeding Users...")
            await seed_users(db, org.id, admin_role.id, owner_role.id)
            
            # 5. Seed Customers, Suppliers, Accounts (requires org_id)
            print("\n[5/5] Seeding Customers, Suppliers, and Accounts...")
            await seed_customers_suppliers(db, org.id)
            await seed_accounts(db, org.id)
            
            print("\n" + "=" * 70)
            print("SEED DATA INITIALIZATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nTest Credentials:")
            print("  Email: admin@sme.com")
            print("  Password: 123456")
            print("  Roles: owner, admin")
            print("=" * 70 + "\n")
            
        except Exception as e:
            await db.rollback()
            print(f"\nERROR during seeding: {str(e)}")
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(run_all_seeds())
```

### Run Seed Data
```bash
# Execute from inside container
docker exec -it sme-backend python app/db/seeds/run_all.py

# Expected output:
# ======================================================================
# STARTING SEED DATA INITIALIZATION
# ======================================================================
# 
# [1/5] Seeding Roles...
#   Created role: owner
#   Created role: admin
#   Created role: accountant
#   Created role: cashier
# Roles seed completed!
# 
# [2/5] Seeding Organizations...
#   Created organization: SME Demo Company
# 
# [3/5] Fetching role IDs...
# 
# [4/5] Seeding Users...
#   Created user: admin@sme.com with roles: owner, admin
# 
# [5/5] Seeding Customers, Suppliers, and Accounts...
#   Created customer: Tech Corp
#   Created customer: Retail Ltd
#   Created supplier: Supply Co
#   Created supplier: Material Inc
#   Created account: Cash on Hand (1001)
#   Created account: Bank Account (1002)
# 
# ======================================================================
# SEED DATA INITIALIZATION COMPLETED SUCCESSFULLY!
# ======================================================================
# 
# Test Credentials:
#   Email: admin@sme.com
#   Password: 123456
#   Roles: owner, admin
# ======================================================================
```

### Verify Seed Data
```bash
# Check users
docker exec -it postgres_application_db psql -U postgres -d sme_pulse_oltp -c \
  "SELECT id, email, full_name, org_id, status FROM core.users;"

# Expected: 1 row with admin@sme.com

# Check roles
docker exec -it postgres_application_db psql -U postgres -d sme_pulse_oltp -c \
  "SELECT id, code, name FROM core.roles;"

# Expected: 4 roles (owner, admin, accountant, cashier)

# Check user roles
docker exec -it postgres_application_db psql -U postgres -d sme_pulse_oltp -c \
  "SELECT u.email, r.code FROM core.user_roles ur \
   JOIN core.users u ON ur.user_id = u.id \
   JOIN core.roles r ON ur.role_id = r.id;"

# Expected: 2 rows (admin with owner and admin roles)
```

---

# PHASE 2: Authentication Implementation

## Step 2.1: Create Authentication Schemas

**File:** `app/modules/auth/schemas.py`

```python
"""Authentication Pydantic schemas."""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class UserInfo(BaseModel):
    """User information in login response."""
    id: int
    email: str
    full_name: Optional[str] = None
    org_id: int
    status: str
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with JWT token."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: UserInfo = Field(..., description="User information")
    roles: List[str] = Field(..., description="User roles")


class UserResponse(BaseModel):
    """User response for /auth/me endpoint."""
    id: int
    email: str
    full_name: Optional[str] = None
    org_id: int
    status: str
    roles: List[str] = Field(..., description="User roles")
    
    class Config:
        from_attributes = True
```

## Step 2.2: Create Authentication Service

**File:** `app/modules/auth/service.py`

```python
"""Business logic for authentication."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.core import User, UserRole
from app.core.security import verify_password, create_access_token

logger = logging.getLogger(__name__)


async def authenticate_user(db: AsyncSession, email: str, password: str):
    """
    Authenticate user and return user with roles.
    
    Returns:
        Tuple of (User, [role_codes]) or None if failed
    """
    # Query user with eager loading of roles
    stmt = (
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles).selectinload(UserRole.role))
    )
    user = await db.scalar(stmt)
    
    if not user:
        logger.warning(f"Login attempt with non-existent email: {email}")
        return None
    
    # Verify password
    if not verify_password(password, user.password_hash):
        logger.warning(f"Failed login attempt for: {email}")
        return None
    
    # Check active status
    if user.status != "active":
        logger.warning(f"Login attempt for inactive user: {email}")
        return None
    
    # Extract role codes
    roles = [ur.role.code for ur in user.roles if ur.role]
    
    logger.info(f"Successful authentication for: {email} with roles: {roles}")
    
    return user, roles


def create_user_token(user_id: int, org_id: int, roles: list):
    """
    Create JWT token for user.
    
    Args:
        user_id: User ID
        org_id: Organization ID (for multi-tenancy)
        roles: List of role codes
    
    Returns:
        Tuple of (access_token, expires_in_seconds)
    """
    token_data = {
        "sub": str(user_id),  # Must be string per JWT spec
        "org_id": org_id,
        "roles": roles,
    }
    access_token, expires_in = create_access_token(token_data)
    return access_token, expires_in
```

## Step 2.3: Create Authentication Dependencies

**File:** `app/modules/auth/dependencies.py`

```python
"""Dependency injection for authentication."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.models.core import User, UserRole
from app.core.security import decode_access_token
from app.db.session import get_db

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Validates:
    - Token is valid and not expired
    - User exists and is active
    - org_id in token matches user org_id (multi-tenancy)
    """
    # Decode and validate JWT
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Invalid or expired JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract claims
    user_id = int(payload.get("sub"))
    token_org_id = payload.get("org_id")
    
    # Fetch user
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(UserRole.role))
    )
    user = await db.scalar(stmt)
    
    if not user:
        logger.warning(f"User not found for JWT token: user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    if user.status != "active":
        logger.warning(f"Login attempt for inactive user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )
    
    # Validate multi-tenancy - org_id must match
    if user.org_id != token_org_id:
        logger.warning(
            f"Organization mismatch for user {user.id}: "
            f"token org_id={token_org_id}, user org_id={user.org_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    return user


def requires_roles(allowed_roles: list):
    """
    Authorization decorator - check if user has required roles.
    
    Usage:
        @router.post("/invoices")
        async def create_invoice(
            current_user: User = Depends(requires_roles(["accountant", "admin"]))
        ):
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_roles = [ur.role.code for ur in current_user.roles if ur.role]
        if not any(role in allowed_roles for role in user_roles):
            logger.warning(
                f"Unauthorized role access: user {current_user.id} "
                f"with roles {user_roles} tried to access {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    
    return role_checker
```

## Step 2.4: Create Authentication Router

**File:** `app/modules/auth/router.py`

```python
"""Authentication router - API endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.schemas import LoginRequest, LoginResponse, UserInfo, UserResponse
from app.modules.auth.service import authenticate_user, create_user_token
from app.modules.auth.dependencies import get_current_user
from app.models.core import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login endpoint - authenticate user and return JWT token.
    
    **UC01 - Login**
    """
    # Authenticate user
    result = await authenticate_user(db, credentials.email, credentials.password)
    
    if result is None:
        logger.warning(f"Failed login attempt for: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user, roles = result
    
    # Create JWT token
    access_token, expires_in = create_user_token(
        user_id=user.id,
        org_id=user.org_id,
        roles=roles
    )
    
    logger.info(f"Successful login for user: {user.email} with roles: {roles}")
    
    # Build response
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            org_id=user.org_id,
            status=user.status
        ),
        roles=roles
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    **Protected endpoint for testing JWT validation**
    """
    roles = [ur.role.code for ur in current_user.roles if ur.role]
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        org_id=current_user.org_id,
        status=current_user.status,
        roles=roles
    )
```

## Step 2.5: Register Router in Main App

**File:** `app/main.py` (Update)

```python
# Add this import
from app.modules.auth.router import router as auth_router

# Add this after creating FastAPI app
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)
```

## Step 2.6: Test Phase 2

```bash
# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sme.com","password":"123456"}'

# Expected: 200 OK with token

# Test /auth/me with token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/auth/me

# Expected: 200 OK with user data
```

---

# PHASE 3: Security Middleware & Exception Handling

## Step 3.1: Create Security Middleware

**File:** `app/middleware/security.py`

```python
"""Security middleware for request tracking and rate limiting."""
import time
import uuid
import logging
from typing import Callable
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing to all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter for login endpoint."""
    
    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 5,
        window_seconds: int = 60,
        paths: list = None
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.paths = paths or ["/api/v1/auth/login"]
        self.requests = defaultdict(list)
    
    def _clean_old_requests(self, ip: str, now: datetime):
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests[ip] = [
            (ts, count) for ts, count in self.requests[ip]
            if ts > cutoff
        ]
    
    def _get_request_count(self, ip: str, now: datetime) -> int:
        self._clean_old_requests(ip, now)
        return sum(count for _, count in self.requests[ip])
    
    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path not in self.paths:
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.now()
        
        request_count = self._get_request_count(client_ip, now)
        
        if request_count >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "request_count": request_count,
                }
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too many requests",
                    "detail": f"Rate limit exceeded. Please try again in {self.window_seconds} seconds.",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )
        
        self.requests[client_ip].append((now, 1))
        return await call_next(request)
```

## Step 3.2: Create Exception Handlers

**File:** `app/core/exceptions.py`

```python
"""Custom exceptions and exception handlers."""
import logging
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


# Custom Exceptions
class SMEPulseException(Exception):
    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class AuthenticationError(SMEPulseException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(SMEPulseException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


# Exception Handlers
async def sme_pulse_exception_handler(request: Request, exc: SMEPulseException):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"SMEPulseException: {exc.message}", extra={"request_id": request_id})
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "request_id": request_id,
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": list(error["loc"]),
            "msg": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(f"Validation error", extra={"request_id": request_id, "errors": errors})
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": errors,
            "request_id": request_id,
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={"request_id": request_id},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred.",
            "request_id": request_id,
        }
    )
```

## Step 3.3: Create Logging Configuration

**File:** `app/core/logging_config.py`

```python
"""Logging configuration with structured JSON output."""
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info"
            ]:
                log_data[key] = value
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging():
    """Configure application logging."""
    log_file = Path(settings.BACKEND_LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.BACKEND_LOG_LEVEL)
    root_logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.BACKEND_LOG_LEVEL)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(settings.BACKEND_LOG_LEVEL)
    
    formatter = JSONFormatter()
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    logging.info("Logging configured", extra={
        "log_level": settings.BACKEND_LOG_LEVEL,
        "log_format": settings.BACKEND_LOG_FORMAT,
    })
```

## Step 3.4: Update Main App with Middleware & Handlers

**File:** `app/main.py` (Update)

```python
"""FastAPI Application Entry Point"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.exceptions import (
    SMEPulseException,
    sme_pulse_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.middleware.security import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
)
from app.db.init_db import initialize_database_schemas
from app.modules.auth.router import router as auth_router

# Setup logging first
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    await initialize_database_schemas()
    yield
    pass


app = FastAPI(
    title="SME Pulse Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

if settings.BACKEND_RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.BACKEND_RATE_LIMIT_REQUESTS,
        window_seconds=settings.BACKEND_RATE_LIMIT_WINDOW,
        paths=["/api/v1/auth/login"],
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

app.add_exception_handler(SMEPulseException, sme_pulse_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, general_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "SME Pulse Backend",
        "version": "1.0.0",
        "environment": settings.BACKEND_ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

## Step 3.5: Update Config with Logging Settings

**File:** `app/core/config.py` (Add these fields)

```python
# Add to Settings class:

# Logging
BACKEND_LOG_FORMAT: str = Field(default="json")  # "json" or "text"
BACKEND_LOG_FILE: str = Field(default="logs/app.log")

# Rate Limiting
BACKEND_RATE_LIMIT_ENABLED: bool = Field(default=True)
BACKEND_RATE_LIMIT_REQUESTS: int = Field(default=5)
BACKEND_RATE_LIMIT_WINDOW: int = Field(default=60)  # seconds
```

## Step 3.6: Test Phase 3

```bash
# Restart backend
docker compose restart backend
sleep 10

# Test security headers
curl -i http://localhost:8000/health

# Expected: X-Content-Type-Options, X-Frame-Options, etc. present

# Test rate limiting
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrong"}'
  echo "Request $i"
done

# Expected: Request 6 returns 429 Too Many Requests

# Check logs
docker compose logs backend --tail 20 | grep -i "json"

# Expected: JSON formatted logs
```

---

# PHASE 4: Testing & Verification

## Complete Test Suite

Run all these tests to verify the system:

```bash
# Test 1: Invalid Credentials
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sme.com","password":"wrong"}'
# Expected: 401 Unauthorized

# Test 2: Valid Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sme.com","password":"123456"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"

# Test 3: Valid Token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/auth/me
# Expected: 200 OK with user data

# Test 4: Invalid Token
curl -H "Authorization: Bearer invalid.token" \
  http://localhost:8000/api/v1/auth/me
# Expected: 401 Unauthorized

# Test 5: Validation Error
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sme.com"}'
# Expected: 422 Unprocessable Entity

# Test 6: Check Logs
docker compose logs backend --tail 50
# Expected: All requests logged with request_id, status_code, process_time
```

Refer to `PHASE4_TEST_GUIDE.md` for comprehensive test scenarios.

---

# Troubleshooting

## Issue 1: "Migration not applied"

```bash
# Check migration status
docker exec -it sme-backend alembic current

# If not at latest, run upgrade
docker exec -it sme-backend alembic upgrade head
```

## Issue 2: "Seed data not created"

```bash
# Check if seed ran successfully
docker exec -it sme-backend python app/db/seeds/run_all.py

# If error, check database connection
docker compose ps postgres_application_db
```

## Issue 3: "Token validation fails"

```bash
# Check token expiration time
python3 << 'EOF'
import jwt
import base64
import json

token = "your_token_here"
parts = token.split('.')
payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
decoded = json.loads(base64.urlsafe_b64decode(payload))
print(json.dumps(decoded, indent=2))
EOF
```

## Issue 4: "Rate limiting not working"

```bash
# Check if rate limiting is enabled
grep BACKEND_RATE_LIMIT_ENABLED backend/.env

# Restart backend if changed
docker compose restart backend
```

## Issue 5: "Logs not in JSON format"

```bash
# Check logging configuration
grep BACKEND_LOG_FORMAT backend/.env

# Should be "json" for JSON format
```

---

## Quick Reference: Test Credentials

- **Email:** admin@sme.com
- **Password:** 123456
- **Roles:** owner, admin
- **Organization ID:** 2

---

## Files Created in This Implementation

```
backend/
├── app/
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── security.py
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── dependencies.py
│   │   │   └── router.py
│   ├── core/
│   │   ├── exceptions.py
│   │   ├── logging_config.py
│   │   └── config.py (updated)
│   ├── db/
│   │   └── seeds/
│   │       ├── __init__.py
│   │       ├── seed_roles.py
│   │       ├── seed_organizations.py
│   │       ├── seed_users.py
│   │       ├── seed_customers_suppliers.py
│   │       ├── seed_accounts.py
│   │       └── run_all.py
│   └── main.py (updated)
└── PHASE4_TEST_GUIDE.md
```

---

**Guide Version:** 1.0  
**Last Updated:** 2025-11-20  
**Status:** Complete  

**Next Steps:**
- ✅ PHASE 1-4: Authentication complete
- ⏳ PHASE 5+: Business logic modules (AR, AP, Payments)
