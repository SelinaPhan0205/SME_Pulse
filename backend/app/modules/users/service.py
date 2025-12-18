"""User Management Service Layer - Business Logic with RBAC."""

import logging
from typing import Optional, List
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.core import User, UserRole, Role
from app.schema.users.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)


async def get_users(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
) -> tuple[list[User], int]:
    """
    Get paginated list of users for an organization.
    
    Args:
        db: Database session
        org_id: Organization ID (CRITICAL for multi-tenancy)
        skip: Number of records to skip
        limit: Max records to return
        search: Search query for email/name
        role: Filter by role code
        status: Filter by status (active, inactive)
    
    Returns:
        Tuple of (users list, total count)
    """
    # Build filters
    filters = [User.org_id == org_id]
    
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern)
            )
        )
    
    if status:
        filters.append(User.status == status)
    
    # If role filter provided, join with UserRole
    base_query = select(User).where(and_(*filters))
    
    if role:
        # Join with roles to filter by role code
        base_query = (
            base_query
            .join(User.roles)
            .join(UserRole.role)
            .where(Role.code == role)
        )
    
    # Count total
    count_stmt = select(func.count()).select_from(User).where(and_(*filters))
    if role:
        count_stmt = (
            count_stmt
            .join(User.roles)
            .join(UserRole.role)
            .where(Role.code == role)
        )
    
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Get paginated data with roles loaded
    stmt = (
        base_query
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    users = result.unique().scalars().all()
    
    logger.info(f"Retrieved {len(users)} users for org_id={org_id}")
    return list(users), total


async def get_user(
    db: AsyncSession,
    user_id: int,
    org_id: int,
) -> User:
    """
    Get single user by ID.
    
    CRITICAL: Always filter by org_id to prevent cross-tenant access.
    
    Args:
        db: Database session
        user_id: User ID
        org_id: Organization ID
    
    Returns:
        User object with roles loaded
    
    Raises:
        HTTPException 404: User not found
    """
    stmt = (
        select(User)
        .where(and_(User.id == user_id, User.org_id == org_id))
        .options(selectinload(User.roles).selectinload(UserRole.role))
    )
    result = await db.execute(stmt)
    user = result.unique().scalar_one_or_none()
    
    if not user:
        logger.warning(f"User {user_id} not found for org_id={org_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


async def create_user(
    db: AsyncSession,
    schema: UserCreate,
    org_id: int,
    current_user: User,
) -> User:
    """
    Create new user.
    
    RBAC: Only Owner/Admin can create users.
    Business Rules:
    - Email must be unique within organization
    - Password is hashed before storage
    - User is assigned to specified role
    
    Args:
        db: Database session
        schema: UserCreate schema
        org_id: Organization ID
        current_user: Current authenticated user (for RBAC check)
    
    Returns:
        Created user
    
    Raises:
        HTTPException 403: Insufficient permissions
        HTTPException 400: Email already exists
    """
    # RBAC Check: Only Owner/Admin can create users
    current_user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in current_user_roles):
        logger.warning(f"User {current_user.id} attempted to create user without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner/Admin can create users"
        )
    
    # Check if email already exists in organization
    existing_stmt = select(User).where(
        and_(User.email == schema.email, User.org_id == org_id)
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists in organization"
        )
    
    # Get role by code
    role_stmt = select(Role).where(Role.code == schema.role)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{schema.role}' not found"
        )
    
    # Create user
    user = User(
        email=schema.email,
        full_name=schema.full_name,
        password_hash=get_password_hash(schema.password),
        org_id=org_id,
        status="active",
    )
    db.add(user)
    await db.flush()  # Flush to get user.id
    
    # Assign role
    user_role = UserRole(
        user_id=user.id,
        role_id=role.id,
        org_id=org_id,
    )
    db.add(user_role)
    
    await db.commit()
    await db.refresh(user)
    
    # Load roles
    await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.roles).selectinload(UserRole.role))
    )
    
    logger.info(f"Created user {user.id} ({user.email}) with role {schema.role}")
    return user


async def update_user(
    db: AsyncSession,
    user_id: int,
    schema: UserUpdate,
    org_id: int,
    current_user: User,
) -> User:
    """
    Update user.
    
    RBAC: Only Owner/Admin can update users (except self).
    
    Args:
        db: Database session
        user_id: User ID to update
        schema: UserUpdate schema
        org_id: Organization ID
        current_user: Current authenticated user
    
    Returns:
        Updated user
    
    Raises:
        HTTPException 403: Insufficient permissions
        HTTPException 404: User not found
    """
    # RBAC Check
    current_user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in current_user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner/Admin can update users"
        )
    
    # Get user
    user = await get_user(db, user_id, org_id)
    
    # Update fields
    if schema.full_name is not None:
        user.full_name = schema.full_name
    
    if schema.status is not None:
        user.status = schema.status
    
    if schema.role is not None:
        # Get new role
        role_stmt = select(Role).where(Role.code == schema.role)
        role_result = await db.execute(role_stmt)
        new_role = role_result.scalar_one_or_none()
        
        if not new_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{schema.role}' not found"
            )
        
        # Remove old roles
        await db.execute(
            select(UserRole).where(UserRole.user_id == user.id)
        )
        for ur in user.roles:
            await db.delete(ur)
        
        # Assign new role
        user_role = UserRole(
            user_id=user.id,
            role_id=new_role.id,
            org_id=org_id,
        )
        db.add(user_role)
    
    await db.commit()
    await db.refresh(user)
    
    # Reload with roles
    stmt = (
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.roles).selectinload(UserRole.role))
    )
    result = await db.execute(stmt)
    user = result.unique().scalar_one()
    
    logger.info(f"Updated user {user.id}")
    return user


async def delete_user(
    db: AsyncSession,
    user_id: int,
    org_id: int,
    current_user: User,
) -> None:
    """
    Delete user (soft delete - set status to inactive).
    
    RBAC: Only Owner/Admin can delete users.
    Cannot delete yourself.
    
    Args:
        db: Database session
        user_id: User ID to delete
        org_id: Organization ID
        current_user: Current authenticated user
    
    Raises:
        HTTPException 403: Insufficient permissions
        HTTPException 400: Cannot delete yourself
        HTTPException 404: User not found
    """
    # RBAC Check
    current_user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in current_user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner/Admin can delete users"
        )
    
    # Cannot delete yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Get user
    user = await get_user(db, user_id, org_id)
    
    # Soft delete - set status to inactive
    user.status = "inactive"
    
    await db.commit()
    
    logger.info(f"Deleted user {user.id} (soft delete)")


async def reset_user_password(
    db: AsyncSession,
    user_id: int,
    new_password: str,
    org_id: int,
    current_user: User,
) -> None:
    """
    Reset user password (Admin only).
    
    RBAC: Only Owner/Admin can reset passwords.
    
    Args:
        db: Database session
        user_id: User ID
        new_password: New password (plain text, will be hashed)
        org_id: Organization ID
        current_user: Current authenticated user
    
    Raises:
        HTTPException 403: Insufficient permissions
        HTTPException 404: User not found
    """
    # RBAC Check
    current_user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in current_user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner/Admin can reset passwords"
        )
    
    # Get user
    user = await get_user(db, user_id, org_id)
    
    # Reset password
    user.password_hash = get_password_hash(new_password)
    
    await db.commit()
    
    logger.info(f"Reset password for user {user.id}")
