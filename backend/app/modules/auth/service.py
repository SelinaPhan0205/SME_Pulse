"""Authentication service layer - business logic."""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.core import User, UserRole, Role
from app.core.security import verify_password, create_access_token
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
