"""Authentication router - API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schema.auth import LoginRequest, LoginResponse, UserInfo, UserResponse
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
    
    Args:
        credentials: Email and password
        db: Database session
    
    Returns:
        LoginResponse with JWT token, user info, and roles
    
    Raises:
        HTTPException 401: Invalid credentials
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
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    **Protected endpoint for testing JWT validation**
    
    Args:
        current_user: Current authenticated user from JWT token
    
    Returns:
        UserResponse with user info and roles
    """
    # Extract roles from user
    roles = [ur.role.code for ur in current_user.roles if ur.role]
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        org_id=current_user.org_id,
        status=current_user.status,
        roles=roles
    )
