"""Router Quản lý Người dùng - REST API endpoints cho CRUD Người dùng."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.core import User
from app.modules.auth.dependencies import requires_roles
from app.modules.users import service
from app.schema.users.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    PaginatedUsersResponse,
    ResetPasswordRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/",
    response_model=PaginatedUsersResponse,
    summary="Liệt kê người dùng",
    description="Lấy danh sách phân trang người dùng cho tổ chức hiện tại (Chỉ Chủ sở/Quản trị viên)"
)
async def list_users(
    skip: int = Query(0, ge=0, description="Số bản ghi cần bỏ qua"),
    limit: int = Query(100, ge=1, le=500, description="Kết quả tối đa trả về"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo email hoặc tên"),
    role: Optional[str] = Query(None, description="Lọc theo vai trò: chủ sở, quản trị viên, kế toán, quỹ tín"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: hoạt động, không hoạt động"),
    current_user: User = Depends(requires_roles(["owner", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Liệt kê tất cả người dùng cho tổ chức hiện tại.
    
    **RBAC: Chỉ Chủ sở hữu/Quản trị viên**
    
    **Đa thuê:** Tự động lọc theo org_id của người dùng hiện tại.
    
    Query Parameters:
    - skip: Offset phân trang (mặc định: 0)
    - limit: Kết quả tối đa (mặc định: 100, tối đa: 500)
    - search: Tìm kiếm theo email hoặc tên
    - role: Lọc theo mã vai trò
    - status: Lọc theo trạng thái (hoạt động, không hoạt động)
    
    Trả lại:
    - Danh sách người dùng được phân trang kèm vai trò và tổng số
    """
    users, total = await service.get_users(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        search=search,
        role=role,
        status=status,
    )
    
    # Ánh xạ sang lược đáp ứng
    user_responses = [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            org_id=user.org_id,
            status=user.status,
            roles=[ur.role.code for ur in user.roles if ur.role],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]
    
    return PaginatedUsersResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=user_responses,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Lấy người dùng theo ID",
    description="Truy xuất chi tiết người dùng duy nhất (Chỉ Chủ sở/Quản trị viên)"
)
async def get_user(
    user_id: int,
    current_user: User = Depends(requires_roles(["owner", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy người dùng theo ID.
    
    **RBAC: Chỉ Chủ sở/Quản trị viên**
    
    **Đa thuê:** Chỉ trả lại người dùng nếu nó thuộc tổ chức của người dùng hiện tại.
    
    Tham số đường dẫn:
    - user_id: ID người dùng
    
    Tăng:
    - 404: Người dùng không được tìm thấy hoặc không thuộc tổ chức hiện tại
    """
    user = await service.get_user(
        db=db,
        user_id=user_id,
        org_id=current_user.org_id,
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=user.org_id,
        status=user.status,
        roles=[ur.role.code for ur in user.roles if ur.role],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo người dùng",
    description="Tạo người dùng mới cho tổ chức hiện tại (Chỉ Chủ sở/Quản trị viên)"
)
async def create_user(
    schema: UserCreate,
    current_user: User = Depends(requires_roles(["owner", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo người dùng mới.
    
    **RBAC: Chỉ Chủ sở/Quản trị viên**
    
    **Đa thuê:** Người dùng được tự động gán cho tổ chức của người dùng hiện tại.
    
    **Quy tắc kinh doanh:**
    - Email phải duy nhất trong tổ chức
    - Mật khẩu được băm trước khi lưu
    - Người dùng được gán cho vai trò được chỉ định
    - Trạng thái mặc định là 'hoạt động'
    
    Thân yêu cầu:
    - email: Email người dùng (bắt buộc, duy nhất trong tổ chức)
    - full_name: Tên đầy đủ của người dùng (bắt buộc)
    - password: Mật khẩu người dùng (bắt buộc, tối thiểu 6 ký tự)
    - role: Vai trò người dùng (bắt buộc, một trong: chủ sở, quản trị viên, kế toán, quỹ tín)
    
    Tăng:
    - 400: Email đã tồn tại hoặc vai trò không hợp lệ
    - 403: Quyền không đủ
    """
    user = await service.create_user(
        db=db,
        schema=schema,
        org_id=current_user.org_id,
        current_user=current_user,
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=user.org_id,
        status=user.status,
        roles=[ur.role.code for ur in user.roles if ur.role],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Cập nhật người dùng",
    description="Cập nhật người dùng hiện có (Chỉ Chủ sở/Quản trị viên)"
)
async def update_user(
    user_id: int,
    schema: UserUpdate,
    current_user: User = Depends(requires_roles(["owner", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật người dùng.
    
    **RBAC: Chỉ Chủ sở/Quản trị viên**
    
    **Đa thuê:** Chỉ cho phép cập nhật người dùng nếu nó thuộc tổ chức của người dùng hiện tại.
    
    **Quy tắc kinh doanh:**
    - Tất cả các trường là tùy chọn (cập nhật một phần)
    - Thay đổi vai trò sẽ thay thế các vai trò hiện có
    
    Tham số đường dẫn:
    - user_id: ID người dùng cần cập nhật
    
    Thân yêu cầu:
    - full_name: Tên đầy đủ của người dùng (tùy chọn)
    - role: Vai trò người dùng (tùy chọn)
    - status: Trạng thái người dùng (tùy chọn: hoạt động, không hoạt động)
    
    Tăng:
    - 404: Người dùng không được tìm thấy hoặc không thuộc tổ chức hiện tại
    - 400: Vai trò không hợp lệ
    - 403: Quyền không đủ
    """
    user = await service.update_user(
        db=db,
        user_id=user_id,
        schema=schema,
        org_id=current_user.org_id,
        current_user=current_user,
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=user.org_id,
        status=user.status,
        roles=[ur.role.code for ur in user.roles if ur.role],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa người dùng",
    description="Xóa mềm người dùng (đặt trạng thái thành không hoạt động) (Chỉ Chủ sở/Quản trị viên)"
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(requires_roles(["owner", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Xóa người dùng (xóa mềm).
    
    **RBAC: Chỉ Chủ sở/Quản trị viên**
    
    **Đa thuê:** Chỉ cho phép xóa người dùng nếu nó thuộc tổ chức của người dùng hiện tại.
    
    **Ghi chú:** Đây là xóa mềm - đặt status='không hoạt động' thay vì xóa khỏi cơ sở dữ liệu.
    
    **Quy tắc kinh doanh:**
    - Không thể xóa chính bạn
    
    Tham số đường dẫn:
    - user_id: ID người dùng cần xóa
    
    Tăng:
    - 404: Người dùng không được tìm thấy hoặc không thuộc tổ chức hiện tại
    - 400: Cố gắng xóa chính bạn
    - 403: Quyền không đủ
    """
    await service.delete_user(
        db=db,
        user_id=user_id,
        org_id=current_user.org_id,
        current_user=current_user,
    )
    
    return None


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Đặt lại mật khẩu người dùng",
    description="Đặt lại mật khẩu người dùng (Chỉ Chủ sở/Quản trị viên)"
)
async def reset_user_password(
    user_id: int,
    schema: ResetPasswordRequest,
    current_user: User = Depends(requires_roles(["owner", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Đặt lại mật khẩu người dùng (Chỉ Quản trị viên).
    
    **RBAC: Chỉ Chủ sở/Quản trị viên**
    
    **Đa thuê:** Chỉ cho phép đặt lại mật khẩu cho những người dùng trong tổ chức của người dùng hiện tại.
    
    Tham số đường dẫn:
    - user_id: ID người dùng
    
    Thân yêu cầu:
    - new_password: Mật khẩu mới (tối thiểu 6 ký tự)
    
    Tăng:
    - 404: Người dùng không được tìm thấy hoặc không thuộc tổ chức hiện tại
    - 403: Quyền không đủ
    """
    await service.reset_user_password(
        db=db,
        user_id=user_id,
        new_password=schema.new_password,
        org_id=current_user.org_id,
        current_user=current_user,
    )
    
    return {"message": "Mật khẩu đã được đặt lại thành công"}
