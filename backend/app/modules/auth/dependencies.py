"""Authentication dependencies for FastAPI."""

import logging
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.core import User, UserRole
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

# OAuth2 scheme for JWT token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decode JWT token and return current authenticated user.
    
    Validates:
    - Token signature and expiry
    - User exists in database
    - User is active
    - Multi-tenancy (org_id matches)
    
    Raises:
        HTTPException 401: Invalid credentials
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decode JWT token
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Invalid or expired JWT token")
        raise credentials_exception
    
    # Extract user_id from token (sub is string per JWT spec)
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        logger.warning("JWT token missing 'sub' claim")
        raise credentials_exception
    
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid user_id in token: {user_id_str}")
        raise credentials_exception
    
    # Query user with eager loading of roles
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"User ID {user_id} from token not found")
        raise credentials_exception
    
    # Validate user is active
    if user.status != "active":
        logger.warning(f"Inactive user {user.email} attempted access")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    # Multi-tenancy check: token org_id must match user's org_id
    token_org_id = payload.get("org_id")
    if token_org_id and token_org_id != user.org_id:
        logger.error(f"Token org_id {token_org_id} != user org_id {user.org_id}")
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Wrapper dependency to ensure user is active.
    (Redundant with get_current_user, but kept for semantic clarity)
    """
    return current_user


def requires_roles(allowed_roles: List[str]):
    """
    Dependency factory for role-based authorization.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(requires_roles(["owner", "admin"]))])
    
    Args:
        allowed_roles: List of role codes allowed
    
    Returns:
        Dependency function
    
    Raises:
        HTTPException 403: User doesn't have required role
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Extract user's role codes
        user_roles = [ur.role.code for ur in current_user.roles if ur.role]
        
        # Check if user has any of the allowed roles
        if not any(role in allowed_roles for role in user_roles):
            logger.warning(
                f"User {current_user.email} with roles {user_roles} "
                f"attempted access requiring {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {allowed_roles}",
            )
        
        return current_user
    
    return role_checker
