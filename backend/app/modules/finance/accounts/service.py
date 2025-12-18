"""Account Management Service Layer - Business Logic for Bank/Cash Accounts."""

import logging
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.core import Account
from app.schema.finance.account import AccountCreate, AccountUpdate

logger = logging.getLogger(__name__)


async def get_accounts(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    account_type: Optional[str] = None,
) -> tuple[list[Account], int]:
    """
    Get paginated list of accounts for an organization.
    
    Args:
        db: Database session
        org_id: Organization ID (CRITICAL for multi-tenancy)
        skip: Number of records to skip
        limit: Max records to return
        is_active: Filter by active status (optional)
        account_type: Filter by type: cash, bank (optional)
    
    Returns:
        Tuple of (accounts list, total count)
    """
    # Build filters
    filters = [Account.org_id == org_id]
    
    if is_active is not None:
        filters.append(Account.is_active == is_active)
    
    if account_type:
        filters.append(Account.type == account_type)
    
    # Count total
    count_stmt = select(func.count()).select_from(Account).where(and_(*filters))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Get paginated data
    stmt = (
        select(Account)
        .where(and_(*filters))
        .order_by(Account.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    
    logger.info(f"Retrieved {len(accounts)} accounts for org_id={org_id}")
    return list(accounts), total


async def get_account(
    db: AsyncSession,
    account_id: int,
    org_id: int,
) -> Account:
    """
    Get single account by ID.
    
    CRITICAL: Always filter by org_id to prevent cross-tenant access.
    
    Args:
        db: Database session
        account_id: Account ID
        org_id: Organization ID
    
    Returns:
        Account object
    
    Raises:
        HTTPException 404: Account not found
    """
    stmt = select(Account).where(
        and_(
            Account.id == account_id,
            Account.org_id == org_id
        )
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    
    if not account:
        logger.warning(f"Account {account_id} not found for org_id={org_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return account


async def create_account(
    db: AsyncSession,
    schema: AccountCreate,
    org_id: int,
) -> Account:
    """
    Create new account.
    
    Business Rules:
    - Account name should be unique within organization (warning only)
    - Type must be 'cash' or 'bank'
    
    Args:
        db: Database session
        schema: AccountCreate schema
        org_id: Organization ID
    
    Returns:
        Created account
    
    Raises:
        HTTPException 400: Invalid account type
    """
    # Validate type
    if schema.type not in ['cash', 'bank']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account type must be 'cash' or 'bank'"
        )
    
    # Create account
    account = Account(
        name=schema.name,
        type=schema.type,
        account_number=schema.account_number,
        bank_name=schema.bank_name,
        org_id=org_id,
        is_active=True,
    )
    
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    logger.info(f"Created account {account.id} ({account.name}) for org_id={org_id}")
    return account


async def update_account(
    db: AsyncSession,
    account_id: int,
    schema: AccountUpdate,
    org_id: int,
) -> Account:
    """
    Update account.
    
    Args:
        db: Database session
        account_id: Account ID to update
        schema: AccountUpdate schema
        org_id: Organization ID
    
    Returns:
        Updated account
    
    Raises:
        HTTPException 404: Account not found
    """
    # Get account
    account = await get_account(db, account_id, org_id)
    
    # Update fields
    if schema.name is not None:
        account.name = schema.name
    
    if schema.account_number is not None:
        account.account_number = schema.account_number
    
    if schema.bank_name is not None:
        account.bank_name = schema.bank_name
    
    if schema.is_active is not None:
        account.is_active = schema.is_active
    
    await db.commit()
    await db.refresh(account)
    
    logger.info(f"Updated account {account.id}")
    return account


async def delete_account(
    db: AsyncSession,
    account_id: int,
    org_id: int,
) -> None:
    """
    Delete account (soft delete - set is_active to False).
    
    Args:
        db: Database session
        account_id: Account ID to delete
        org_id: Organization ID
    
    Raises:
        HTTPException 404: Account not found
    """
    # Get account
    account = await get_account(db, account_id, org_id)
    
    # Soft delete
    account.is_active = False
    
    await db.commit()
    
    logger.info(f"Deleted account {account.id} (soft delete)")
