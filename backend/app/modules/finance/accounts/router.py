"""Account Management Router - REST API endpoints for Bank/Cash Accounts."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.core import User
from app.modules.auth.dependencies import get_current_user
from app.modules.finance.accounts import service
from app.schema.finance.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    PaginatedAccountsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get(
    "/",
    response_model=PaginatedAccountsResponse,
    summary="List accounts",
    description="Get paginated list of bank/cash accounts for current organization"
)
async def list_accounts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    account_type: Optional[str] = Query(None, description="Filter by type: cash, bank"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all accounts for current organization.
    
    **Multi-tenancy:** Automatically filters by current user's org_id.
    
    Query Parameters:
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 100, max: 500)
    - is_active: Filter active/inactive accounts
    - account_type: Filter by type (cash, bank)
    
    Returns:
    - Paginated list of accounts with total count
    """
    accounts, total = await service.get_accounts(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        is_active=is_active,
        account_type=account_type,
    )
    
    return PaginatedAccountsResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[AccountResponse.model_validate(acc) for acc in accounts],
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account by ID",
    description="Retrieve single account details"
)
async def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get account by ID.
    
    **Multi-tenancy:** Only returns account if it belongs to current user's organization.
    
    Path Parameters:
    - account_id: Account ID
    
    Raises:
    - 404: Account not found or doesn't belong to current organization
    """
    account = await service.get_account(
        db=db,
        account_id=account_id,
        org_id=current_user.org_id,
    )
    return AccountResponse.model_validate(account)


@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account",
    description="Create new bank/cash account for current organization"
)
async def create_account(
    schema: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new account.
    
    **Multi-tenancy:** Account is automatically assigned to current user's organization.
    
    **Business Rules:**
    - Type must be 'cash' or 'bank'
    - account_number and bank_name required for bank accounts (optional for cash)
    
    Request Body:
    - name: Account name (required)
    - type: Account type (required, one of: cash, bank)
    - account_number: Account number (optional, for bank accounts)
    - bank_name: Bank name (optional, for bank accounts)
    
    Raises:
    - 400: Invalid account type
    """
    account = await service.create_account(
        db=db,
        schema=schema,
        org_id=current_user.org_id,
    )
    return AccountResponse.model_validate(account)


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account",
    description="Update existing account"
)
async def update_account(
    account_id: int,
    schema: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update account.
    
    **Multi-tenancy:** Only allows updating account if it belongs to current user's organization.
    
    **Business Rules:**
    - All fields are optional (partial update)
    - Cannot change account type
    
    Path Parameters:
    - account_id: Account ID to update
    
    Request Body:
    - name: Account name (optional)
    - account_number: Account number (optional)
    - bank_name: Bank name (optional)
    - is_active: Active status (optional)
    
    Raises:
    - 404: Account not found or doesn't belong to current organization
    """
    account = await service.update_account(
        db=db,
        account_id=account_id,
        schema=schema,
        org_id=current_user.org_id,
    )
    return AccountResponse.model_validate(account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account",
    description="Soft delete account (set is_active=False)"
)
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete account (soft delete).
    
    **Multi-tenancy:** Only allows deleting account if it belongs to current user's organization.
    
    **Note:** This is a soft delete - sets is_active=False instead of removing from database.
    
    Path Parameters:
    - account_id: Account ID to delete
    
    Raises:
    - 404: Account not found or doesn't belong to current organization
    """
    await service.delete_account(
        db=db,
        account_id=account_id,
        org_id=current_user.org_id,
    )
    return None
