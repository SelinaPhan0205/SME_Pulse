"""Service Layer Quản lý Người dùng - Logic kinh doanh với RBAC."""

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
    Lấy danh sách người dùng được phân trang cho một tổ chức.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        org_id: ID tổ chức (QUAN TRỌNG để đa thuê)
        skip: Số bản ghi cần bỏ qua
        limit: Tối đa bản ghi trả về
        search: Truy vấn tìm kiếm cho email/tên
        role: Lọc theo mã vai trò
        status: Lọc theo trạng thái (hoạt động, không hoạt động)
    
    Trả lại:
        Tuple của (danh sách người dùng, tổng số)
    """
    # Xây dựng bộ lọc
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
    
    # Nếu cung cấp bộ lọc vai trò, hãy nối với UserRole
    base_query = select(User).where(and_(*filters))
    
    if role:
        # Nối với vai trò để lọc theo mã vai trò
        base_query = (
            base_query
            .join(User.roles)
            .join(UserRole.role)
            .where(Role.code == role)
        )
    
    # Đếm tổng số
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
    
    # Lấy dữ liệu được phân trang với vai trò được tải
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
    Lấy một người dùng theo ID.
    
    QUAN TRỌNG: Luôn lọc theo org_id để ngăn chặn truy cập đa thuê.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        user_id: ID người dùng
        org_id: ID tổ chức
    
    Trả lại:
        Đối tượng người dùng với các vai trò được tải
    
    Tăng:
        HTTPException 404: Người dùng không được tìm thấy
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
            detail="Người dùng không được tìm thấy"
        )
    
    return user


async def create_user(
    db: AsyncSession,
    schema: UserCreate,
    org_id: int,
    current_user: User,
) -> User:
    """
    Tạo người dùng mới.
    
    RBAC: Chỉ Chủ sở/Quản trị viên mới có thể tạo người dùng.
    Quy tắc kinh doanh:
    - Email phải duy nhất trong tổ chức
    - Mật khẩu được băm trước khi lưu
    - Người dùng được gán cho vai trò được chỉ định
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        schema: Lược đồ UserCreate
        org_id: ID tổ chức
        current_user: Người dùng được xác thực hiện tại (để kiểm tra RBAC)
    
    Trả lại:
        Người dùng được tạo
    
    Tăng:
        HTTPException 403: Quyền không đủ
        HTTPException 400: Email đã tồn tại
    """
    # Kiểm tra RBAC: Chỉ Owner/Admin mới có thể tạo người dùng
    current_user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in current_user_roles):
        logger.warning(f"User {current_user.id} attempted to create user without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Chủ sở/Quản trị viên mới có thể tạo người dùng"
        )
    
    # Kiểm tra nếu email đã tồn tại trong tổ chức
    existing_stmt = select(User).where(
        and_(User.email == schema.email, User.org_id == org_id)
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã tồn tại trong tổ chức"
        )
    
    # Lấy vai trò theo mã
    role_stmt = select(Role).where(Role.code == schema.role)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vai trò '{schema.role}' không được tìm thấy"
        )
    
    # Tạo người dùng
    user = User(
        email=schema.email,
        full_name=schema.full_name,
        password_hash=get_password_hash(schema.password),
        org_id=org_id,
        status="active",
    )
    db.add(user)
    await db.flush()  # Xả để lấy user.id
    
    # Gán vai trò
    user_role = UserRole(
        user_id=user.id,
        role_id=role.id,
        org_id=org_id,
    )
    db.add(user_role)
    
    await db.commit()
    await db.refresh(user)
    
    # Tải vai trò
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
    Cập nhật người dùng.
    
    RBAC: Chỉ Chủ sở/Quản trị viên mới có thể cập nhật người dùng (ngoại trừ chính bản thân).
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        user_id: ID người dùng cần cập nhật
        schema: Lược đồ UserUpdate
        org_id: ID tổ chức
        current_user: Người dùng được xác thực hiện tại
    
    Trả lại:
        Người dùng được cập nhật
    
    Tăng:
        HTTPException 403: Quyền không đủ
        HTTPException 404: Người dùng không được tìm thấy
    """
    # RBAC Kiểm tra
    current_user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in current_user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Chủ sở/Quản trị viên mới có thể cập nhật người dùng"
        )
    
    # Lấy người dùng
    user = await get_user(db, user_id, org_id)
    
    # Cập nhật các trường
    if schema.full_name is not None:
        user.full_name = schema.full_name
    
    if schema.status is not None:
        user.status = schema.status
    
    if schema.role is not None:
    # Lấy vai trò mới
        role_stmt = select(Role).where(Role.code == schema.role)
        role_result = await db.execute(role_stmt)
        new_role = role_result.scalar_one_or_none()
        
        if not new_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vai trò '{schema.role}' không được tìm thấy"
            )
        
        # Xóa vai trò cũ
        await db.execute(
            select(UserRole).where(UserRole.user_id == user.id)
        )
        for ur in user.roles:
            await db.delete(ur)
        
        # Gán vai trò mới
        user_role = UserRole(
            user_id=user.id,
            role_id=new_role.id,
            org_id=org_id,
        )
        db.add(user_role)
    
    await db.commit()
    await db.refresh(user)
    
    # Tải lại với vai trò
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
    Xóa người dùng (xóa mềm - đặt trạng thái thành không hoạt động).
    
    RBAC: Chỉ Chủ sở/Quản trị viên mới có thể xóa người dùng.
    Không thể xóa chính bạn.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        user_id: ID người dùng cần xóa
        org_id: ID tổ chức
        current_user: Người dùng được xác thực hiện tại
    
    Tăng:
        HTTPException 403: Quyền không đủ
        HTTPException 400: Không thể xóa chính bạn
        HTTPException 404: Người dùng không được tìm thấy
    """
    # Kiểm tra RBAC
    current_user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in current_user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Chủ sở/Quản trị viên mới có thể xóa người dùng"
        )
    
    # Không thể xóa chính bạn
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa chính bạn"
        )
    
    # Lấy người dùng
    user = await get_user(db, user_id, org_id)
    
    # Xóa mềm - đặt trạng thái thành không hoạt động
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
    Đặt lại mật khẩu người dùng (Chỉ Quản trị viên).
    
    RBAC: Chỉ Chủ sở/Quản trị viên mới có thể đặt lại mật khẩu.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        user_id: ID người dùng
        new_password: Mật khẩu mới (văn bản thuần túy, sẽ được băm)
        org_id: ID tổ chức
        current_user: Người dùng được xác thực hiện tại
    
    Tăng:
        HTTPException 403: Quyền không đủ
        HTTPException 404: Người dùng không được tìm thấy
    """
    # RBAC Kiểm tra
    current_user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in current_user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Chủ sở/Quản trị viên mới có thể đặt lại mật khẩu"
        )
    
    # Lấy người dùng
    user = await get_user(db, user_id, org_id)
    
    # Đặt lại mật khẩu
    user.password_hash = get_password_hash(new_password)
    
    await db.commit()
    
    logger.info(f"Reset password for user {user.id}")
