"""User Management Router - REST API endpoints for Users CRUD."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.core import User
from app.modules.auth.dependencies import get_current_user
from app.modules.users import service
from app.schema.users.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    PaginatedUsersResponse,
    ResetPasswordRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/",
    response_model=PaginatedUsersResponse,
    summary="List users",
    description="Get paginated list of users for current organization (Owner/Admin only)"
)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    role: Optional[str] = Query(None, description="Filter by role: owner, admin, accountant, cashier"),
    status: Optional[str] = Query(None, description="Filter by status: active, inactive"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users for current organization.
    
    **RBAC: Owner/Admin only**
    
    **Multi-tenancy:** Automatically filters by current user's org_id.
    
    Query Parameters:
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 100, max: 500)
    - search: Search by email or full name
    - role: Filter by role code
    - status: Filter by status (active, inactive)
    
    Returns:
    - Paginated list of users with roles and total count
    """
    users, total = await service.get_users(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        search=search,
        role=role,
        status=status,
    )
    
    # Map to response schema
    user_responses = [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            org_id=user.org_id,
            status=user.status,
            roles=[ur.role.code for ur in user.roles if ur.role],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]
    
    return PaginatedUsersResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=user_responses,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve single user details (Owner/Admin only)"
)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user by ID.
    
    **RBAC: Owner/Admin only**
    
    **Multi-tenancy:** Only returns user if it belongs to current user's organization.
    
    Path Parameters:
    - user_id: User ID
    
    Raises:
    - 404: User not found or doesn't belong to current organization
    """
    user = await service.get_user(
        db=db,
        user_id=user_id,
        org_id=current_user.org_id,
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=user.org_id,
        status=user.status,
        roles=[ur.role.code for ur in user.roles if ur.role],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create new user for current organization (Owner/Admin only)"
)
async def create_user(
    schema: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new user.
    
    **RBAC: Owner/Admin only**
    
    **Multi-tenancy:** User is automatically assigned to current user's organization.
    
    **Business Rules:**
    - Email must be unique within organization
    - Password is hashed before storage
    - User is assigned to specified role
    - Default status is 'active'
    
    Request Body:
    - email: User email (required, unique within org)
    - full_name: User full name (required)
    - password: User password (required, min 6 chars)
    - role: User role (required, one of: owner, admin, accountant, cashier)
    
    Raises:
    - 400: Email already exists or invalid role
    - 403: Insufficient permissions
    """
    user = await service.create_user(
        db=db,
        schema=schema,
        org_id=current_user.org_id,
        current_user=current_user,
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=user.org_id,
        status=user.status,
        roles=[ur.role.code for ur in user.roles if ur.role],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update existing user (Owner/Admin only)"
)
async def update_user(
    user_id: int,
    schema: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user.
    
    **RBAC: Owner/Admin only**
    
    **Multi-tenancy:** Only allows updating user if it belongs to current user's organization.
    
    **Business Rules:**
    - All fields are optional (partial update)
    - Role change will replace existing roles
    
    Path Parameters:
    - user_id: User ID to update
    
    Request Body:
    - full_name: User full name (optional)
    - role: User role (optional)
    - status: User status (optional: active, inactive)
    
    Raises:
    - 404: User not found or doesn't belong to current organization
    - 400: Invalid role
    - 403: Insufficient permissions
    """
    user = await service.update_user(
        db=db,
        user_id=user_id,
        schema=schema,
        org_id=current_user.org_id,
        current_user=current_user,
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=user.org_id,
        status=user.status,
        roles=[ur.role.code for ur in user.roles if ur.role],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Soft delete user (set status to inactive) (Owner/Admin only)"
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete user (soft delete).
    
    **RBAC: Owner/Admin only**
    
    **Multi-tenancy:** Only allows deleting user if it belongs to current user's organization.
    
    **Note:** This is a soft delete - sets status='inactive' instead of removing from database.
    
    **Business Rules:**
    - Cannot delete yourself
    
    Path Parameters:
    - user_id: User ID to delete
    
    Raises:
    - 404: User not found or doesn't belong to current organization
    - 400: Attempt to delete yourself
    - 403: Insufficient permissions
    """
    await service.delete_user(
        db=db,
        user_id=user_id,
        org_id=current_user.org_id,
        current_user=current_user,
    )
    
    return None


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset user password",
    description="Reset user password (Owner/Admin only)"
)
async def reset_user_password(
    user_id: int,
    schema: ResetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reset user password (Admin only).
    
    **RBAC: Owner/Admin only**
    
    **Multi-tenancy:** Only allows resetting password for users in current user's organization.
    
    Path Parameters:
    - user_id: User ID
    
    Request Body:
    - new_password: New password (min 6 chars)
    
    Raises:
    - 404: User not found or doesn't belong to current organization
    - 403: Insufficient permissions
    """
    await service.reset_user_password(
        db=db,
        user_id=user_id,
        new_password=schema.new_password,
        org_id=current_user.org_id,
        current_user=current_user,
    )
    
    return {"message": "Password reset successfully"}
