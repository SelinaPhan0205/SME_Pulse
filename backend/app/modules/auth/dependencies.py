"""Các dependencies xác thực cho FastAPI."""

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

# Sơ đồ OAuth2 cho JWT token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Giải mã JWT token và trả về người dùng đã xác thực hiện tại.
    
    Xác thực:
    - Chữ ký token và hết hạn
    - Người dùng tồn tại trong cơ sở dữ liệu
    - Người dùng hoạt động
    - Đa thuê (org_id khớp)
    
    Tăng:
        HTTPException 401: Thông tin xác thực không hợp lệ
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin xác thực",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Giải mã JWT token
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("JWT token không hợp lệ hoặc đã hết hạn")
        raise credentials_exception
    
    # Trích xuất user_id từ token (sub là chuỗi theo thông số kỹ thuật JWT)
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        logger.warning("JWT token bị thiếu claim 'sub'")
        raise credentials_exception
    
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.warning(f"ID người dùng không hợp lệ trong token: {user_id_str}")
        raise credentials_exception
    
    # Truy vấn người dùng với tải sẵn vai trò
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"ID người dùng {user_id} từ token không được tìm thấy")
        raise credentials_exception
    
    # Xác thực người dùng hoạt động
    if user.status != "active":
        logger.warning(f"Người dùng không hoạt động {user.email} cố gắng truy cập")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản người dùng không hoạt động",
        )
    
    # Kiểm tra đa thuê: org_id của token phải khớp với org_id của người dùng
    token_org_id = payload.get("org_id")
    if token_org_id and token_org_id != user.org_id:
        logger.error(f"Token org_id {token_org_id} != user org_id {user.org_id}")
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Wrapper dependency để đảm bảo người dùng hoạt động.
    (Dư thừa với get_current_user, nhưng được giữ lại để rõ ràng từ ngữ)
    """
    return current_user


def requires_roles(allowed_roles: List[str]):
    """
    Nhà máy dependencies cho ủy quyền dựa trên vai trò.
    
    Cách sử dụng:
        @router.get("/admin", dependencies=[Depends(requires_roles(["owner", "admin"]))])
    
    Đối số:
        allowed_roles: Danh sách mã vai trò được phép
    
    Trả lại:
        Hàm dependency
    
    Tăng:
        HTTPException 403: Người dùng không có vai trò được yêu cầu
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Trích xuất mã vai trò của người dùng
        user_roles = [ur.role.code for ur in current_user.roles if ur.role]
        
        # Kiểm tra xem người dùng có bất kỳ vai trò được phép nào không
        if not any(role in allowed_roles for role in user_roles):
            logger.warning(
                f"Người dùng {current_user.email} có vai trò {user_roles} "
                f"cố gắng truy cập yêu cầu {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vai trò được yêu cầu: {allowed_roles}",
            )
        
        return current_user
    
    return role_checker
