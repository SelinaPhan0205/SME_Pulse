"""Router xác thực - API endpoints."""

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
    Endpoint đăng nhập - xác thực người dùng và trả về JWT token.
    
    **UC01 - Đăng nhập**
    
    Đối số:
        credentials: Email và mật khẩu
        db: Phiên cơ sở dữ liệu
    
    Trả lại:
        LoginResponse với JWT token, thông tin người dùng và vai trò
    
    Tăng:
        HTTPException 401: Thông tin xác thực không hợp lệ
    """
    # Xác thực người dùng
    result = await authenticate_user(db, credentials.email, credentials.password)
    
    if result is None:
        logger.warning(f"Cố gắng đăng nhập thất bại cho: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user, roles = result
    
    # Tạo JWT token
    access_token, expires_in = create_user_token(
        user_id=user.id,
        org_id=user.org_id,
        roles=roles
    )
    
    logger.info(f"Đăng nhập thành công cho người dùng: {user.email} với vai trò: {roles}")
    
    # Xây dựng phản hồi
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
    Lấy thông tin người dùng đã xác thực hiện tại.
    
    **Endpoint được bảo vệ để kiểm tra xác thực JWT**
    
    Đối số:
        current_user: Người dùng đã xác thực hiện tại từ JWT token
    
    Trả lại:
        UserResponse với thông tin người dùng và vai trò
    """
    # Trích xuất vai trò từ người dùng
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
    Thay đổi mật khẩu của người dùng hiện tại.
    
    **Endpoint được bảo vệ - yêu cầu xác thực**
    
    Đối số:
        request: Mật khẩu cũ và mới
        current_user: Người dùng đã xác thực hiện tại
        db: Phiên cơ sở dữ liệu
    
    Trả lại:
        Thông báo thành công
    
    Tăng:
        HTTPException 400: Mật khẩu cũ không chính xác hoặc xác thực thất bại
    """
    await change_user_password(
        db=db,
        user=current_user,
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    logger.info(f"Mật khẩu đã thay đổi cho người dùng: {current_user.email}")
    
    return {"message": "Mật khẩu đã được thay đổi thành công"}


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Bắt đầu quy trình quên mật khẩu.
    
    **Endpoint công khai**
    
    Gửi hướng dẫn đặt lại mật khẩu đến email của người dùng.
    Để bảo mật, luôn trả lại thành công ngay cả khi email không tồn tại.
    
    Đối số:
        request: Email người dùng
        db: Phiên cơ sở dữ liệu
    
    Trả lại:
        Thông báo thành công với email
    
    Ghi chú:
        Trong sản xuất, điều này sẽ tạo một token đặt lại an toàn,
        lưu nó trong DB và gửi một email với liên kết đặt lại.
        Hiện tại ghi nhật ký yêu cầu để phát triển.
    """
    email = await initiate_password_reset(db=db, email=request.email)
    
    return PasswordResetResponse(
        message="Nếu email tồn tại, hướng dẫn đặt lại mật khẩu đã được gửi",
        email=email
    )
