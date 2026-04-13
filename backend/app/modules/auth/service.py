"""Lớp dịch vụ xác thực - logic kinh doanh."""

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
    Xác thực người dùng theo email và mật khẩu.
    
    Trả lại:
        Tuple của (Người dùng, vai trò) nếu thành công, None nếu không.
    """
    # Truy vấn người dùng với tải sẵn vai trò (tránh N+1)
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.email == email)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    # Kiểm tra người dùng tồn tại
    if not user:
        logger.warning(f"Cố gắng đăng nhập với email không tồn tại: {email}")
        return None
    
    # Xác minh mật khẩu
    if not verify_password(password, user.password_hash):
        logger.warning(f"Đăng nhập thất bại cho người dùng: {email} (mật khẩu không hợp lệ)")
        return None
    
    # Kiểm tra người dùng hoạt động
    if user.status != "active":
        logger.warning(f"Cố gắng đăng nhập cho người dùng không hoạt động: {email} (trạng thái: {user.status})")
        return None
    
    # Trích xuất mã vai trò
    roles = [ur.role.code for ur in user.roles if ur.role]
    
    logger.info(f"Xác thực thành công cho: {email} với vai trò: {roles}")
    return user, roles


def create_user_token(user_id: int, org_id: int, roles: list[str]) -> tuple[str, int]:
    """
    Tạo JWT access token cho người dùng đã xác thực.
    
    Đối số:
        user_id: ID người dùng
        org_id: ID tổ chức (đa thuê)
        roles: Danh sách mã vai trò
    
    Trả lại:
        Tuple của (access_token, hết hạn trong giây)
    """
    # Xây dựng tải token (sub phải là chuỗi theo thông số kỹ thuật JWT)
    token_data = {
        "sub": str(user_id),  # Claim chủ đề JWT phải là chuỗi
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
    Thay đổi mật khẩu người dùng.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        user: Người dùng đã xác thực hiện tại
        old_password: Mật khẩu hiện tại
        new_password: Mật khẩu mới
    
    Tăng:
        HTTPException 400: Mật khẩu cũ không chính xác hoặc mật khẩu mới quá yếu
    """
    # Xác minh mật khẩu cũ
    if not verify_password(old_password, user.password_hash):
        logger.warning(f"Thay đổi mật khẩu thất bại cho người dùng {user.id}: mật khẩu cũ không chính xác")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không chính xác"
        )
    
    # Xác thực độ mạnh mật khẩu mới (tối thiểu 6 ký tự)
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải có ít nhất 6 ký tự"
        )
    
    # Mã hóa và cập nhật mật khẩu
    user.password_hash = get_password_hash(new_password)
    await db.commit()
    
    logger.info(f"Mật khẩu đã thay đổi thành công cho người dùng {user.id}")


async def initiate_password_reset(
    db: AsyncSession,
    email: str
) -> str:
    """
    Bắt đầu quy trình quên mật khẩu.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        email: Email người dùng
    
    Trả lại:
        Địa chỉ email nơi gửi hướng dẫn đặt lại
    
    Ghi chú:
        Trong sản xuất, điều này sẽ:
        1. Tạo token đặt lại an toàn
        2. Lưu token trong DB với thời gian hết hạn
        3. Gửi email với liên kết đặt lại
        
        Hiện tại, chúng ta chỉ ghi nhật ký yêu cầu (bảo mật: không tiết lộ nếu email tồn tại)
    """
    # Truy vấn người dùng (nhưng không tiết lộ nếu tồn tại để bảo mật)
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # TODO: Tạo token đặt lại, lưu trong DB, gửi email
        logger.info(f"Yêu cầu đặt lại mật khẩu cho người dùng {user.id} ({email})")
        # Trong sản xuất: send_password_reset_email(user.email, reset_token)
    else:
        # Bảo mật: Không tiết lộ nếu email tồn tại
        logger.info(f"Yêu cầu đặt lại mật khẩu cho email không tồn tại: {email}")
    
    # Luôn trả lại thành công (đừng rò rỉ sự tồn tại của người dùng)
    return email
