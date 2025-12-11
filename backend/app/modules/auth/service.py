"""Authentication service layer - business logic."""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.core import User, UserRole, Role
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.config import settings

logger = logging.getLogger(__name__)


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str
) -> Optional[tuple[User, list[str]]]:
    """
    Authenticate user by email and password.
    
    Returns:
        Tuple of (User, roles) if successful, None otherwise.
    """
    # Query user with eager loading of roles (avoid N+1)
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.email == email)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    # Check user exists
    if not user:
        logger.warning(f"Login attempt with non-existent email: {email}")
        return None
    
    # Verify password
    if not verify_password(password, user.password_hash):
        logger.warning(f"Failed login for user: {email} (invalid password)")
        return None
    
    # Check user is active
    if user.status != "active":
        logger.warning(f"Login attempt for inactive user: {email} (status: {user.status})")
        return None
    
    # Extract role codes
    roles = [ur.role.code for ur in user.roles if ur.role]
    
    logger.info(f"Successful authentication for: {email} with roles: {roles}")
    return user, roles


def create_user_token(user_id: int, org_id: int, roles: list[str]) -> tuple[str, int]:
    """
    Create JWT access token for authenticated user.
    
    Args:
        user_id: User ID
        org_id: Organization ID (multi-tenancy)
        roles: List of role codes
    
    Returns:
        Tuple of (access_token, expires_in_seconds)
    """
    # Build token payload (sub must be string per JWT spec)
    token_data = {
        "sub": str(user_id),  # JWT subject claim must be string
        "org_id": org_id,
        "roles": roles,
    }
    
    access_token = create_access_token(data=token_data)
    expires_in = settings.BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return access_token, expires_in


async def change_user_password(
    db: AsyncSession,
    user: User,
    old_password: str,
    new_password: str
) -> None:
    """
    Change user password.
    
    Args:
        db: Database session
        user: Current authenticated user
        old_password: Current password
        new_password: New password
    
    Raises:
        HTTPException 400: Old password incorrect or new password too weak
    """
    # Verify old password
    if not verify_password(old_password, user.password_hash):
        logger.warning(f"Failed password change for user {user.id}: incorrect old password")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength (min 6 chars)
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    # Hash and update password
    user.password_hash = get_password_hash(new_password)
    await db.commit()
    
    logger.info(f"Password changed successfully for user {user.id}")


async def initiate_password_reset(
    db: AsyncSession,
    email: str
) -> str:
    """
    Initiate forgot password flow.
    
    Args:
        db: Database session
        email: User email
    
    Returns:
        Email address where reset instructions were sent
    
    Note:
        In production, this should:
        1. Generate secure reset token
        2. Store token in DB with expiry
        3. Send email with reset link
        
        For now, we just log the request (security: don't reveal if email exists)
    """
    # Query user (but don't reveal if exists for security)
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # TODO: Generate reset token, store in DB, send email
        logger.info(f"Password reset requested for user {user.id} ({email})")
        # In production: send_password_reset_email(user.email, reset_token)
    else:
        # Security: Don't reveal if email exists
        logger.info(f"Password reset requested for non-existent email: {email}")
    
    # Always return success (don't leak user existence)
    return email
