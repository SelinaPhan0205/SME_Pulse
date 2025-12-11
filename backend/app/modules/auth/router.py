"""Authentication router - API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schema.auth import (
    LoginRequest, 
    LoginResponse, 
    UserInfo, 
    UserResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    PasswordResetResponse
)
from app.modules.auth.service import (
    authenticate_user, 
    create_user_token,
    change_user_password,
    initiate_password_reset
)
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


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user's password.
    
    **Protected endpoint - requires authentication**
    
    Args:
        request: Old and new passwords
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Success message
    
    Raises:
        HTTPException 400: Old password incorrect or validation failed
    """
    await change_user_password(
        db=db,
        user=current_user,
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    logger.info(f"Password changed for user: {current_user.email}")
    
    return {"message": "Password changed successfully"}


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate forgot password flow.
    
    **Public endpoint**
    
    Sends password reset instructions to user's email.
    For security, always returns success even if email doesn't exist.
    
    Args:
        request: User email
        db: Database session
    
    Returns:
        Success message with email
    
    Note:
        In production, this should generate a secure reset token,
        store it in DB, and send an email with reset link.
        Currently logs the request for development.
    """
    email = await initiate_password_reset(db=db, email=request.email)
    
    return PasswordResetResponse(
        message="If the email exists, password reset instructions have been sent",
        email=email
    )
