"""Router Quản lý Tài khoản - REST API endpoints cho Tài khoản Ngân hàng/Tiền mặt."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.core import User
from app.modules.auth.dependencies import get_current_user
from app.modules.finance.accounts import service
from app.schema.finance.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    PaginatedAccountsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get(
    "/",
    response_model=PaginatedAccountsResponse,
    summary="Liệt kê tài khoản",
    description="Lấy danh sách phân trang các tài khoản ngân hàng/tiền mặt cho tổ chức hiện tại"
)
async def list_accounts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    account_type: Optional[str] = Query(None, description="Filter by type: cash, bank"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Liệt kê tất cả tài khoản cho tổ chức hiện tại.
    
    **Multi-tenancy:** Tự động lọc theo org_id của người dùng hiện tại.
    
    Tham số truy vấn:
    - skip: Độ lệch phân trang (mặc định: 0)
    - limit: Kết quả tối đa (mặc định: 100, tối đa: 500)
    - is_active: Lọc tài khoản hoạt động/bị tắt
    - account_type: Lọc theo loại (cash, bank)
    
    Trả về:
    - Danh sách tài khoản phân trang với tổng số
    """
    accounts, total = await service.get_accounts(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        is_active=is_active,
        account_type=account_type,
    )
    
    return PaginatedAccountsResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[AccountResponse.model_validate(acc) for acc in accounts],
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Lấy tài khoản theo ID",
    description="Truy xuất chi tiết tài khoản duy nhất"
)
async def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy tài khoản theo ID.
    
    **Multi-tenancy:** Chỉ trả về tài khoản nếu nó thuộc tổ chức của người dùng hiện tại.
    
    Tham số đường dẫn:
    - account_id: ID tài khoản
    
    Nâng cao:
    - 404: Tài khoản không tập hoặc không thuộc tổ chức hiện tại
    """
    account = await service.get_account(
        db=db,
        account_id=account_id,
        org_id=current_user.org_id,
    )
    return AccountResponse.model_validate(account)


@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tài khoản",
    description="Tạo tài khoản ngân hàng/tiền mặt mới cho tổ chức hiện tại"
)
async def create_account(
    schema: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo tài khoản mới.
    
    **Multi-tenancy:** Tài khoản được tự động gán cho tổ chức của người dùng hiện tại.
    
    **Quy tắc kinh doanh:**
    - Loại phải là 'cash' hoặc 'bank'
    - account_number và bank_name bắt buộc cho tài khoản ngân hàng (tùy chọn cho tiền mặt)
    
    Thân yêu cầu:
    - name: Tên tài khoản (bắt buộc)
    - type: Loại tài khoản (bắt buộc, một trong: cash, bank)
    - account_number: Số tài khoản (tùy chọn, cho tài khoản ngân hàng)
    - bank_name: Tên ngân hàng (tùy chọn, cho tài khoản ngân hàng)
    
    Nâng cao:
    - 400: Loại tài khoản không hợp lệ
    """
    account = await service.create_account(
        db=db,
        schema=schema,
        org_id=current_user.org_id,
    )
    return AccountResponse.model_validate(account)


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Cập nhật tài khoản",
    description="Cập nhật tài khoản hiện có"
)
async def update_account(
    account_id: int,
    schema: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật tài khoản.
    
    **Multi-tenancy:** Chỉ cho phép cập nhật tài khoản nếu nó thuộc tổ chức của người dùng hiện tại.
    
    **Quy tắc kinh doanh:**
    - Tất cả các trường là tùy chọn (cập nhật mặt khóa cơ)
    - Không thể thay đổi loại tài khoản
    
    Tham số đường dẫn:
    - account_id: ID tài khoản cần cập nhật
    
    Thân yêu cầu:
    - name: Tên tài khoản (tùy chọn)
    - account_number: Số tài khoản (tùy chọn)
    - bank_name: Tên ngân hàng (tùy chọn)
    - is_active: Trạng thái hoạt động (tùy chọn)
    
    Nâng cao:
    - 404: Tài khoản không tập hoặc không thuộc tổ chức hiện tại
    """
    account = await service.update_account(
        db=db,
        account_id=account_id,
        schema=schema,
        org_id=current_user.org_id,
    )
    return AccountResponse.model_validate(account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa tài khoản",
    description="Xóa mềm tài khoản (đặt is_active=False)"
)
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Xóa tài khoản (soft delete).
    
    **Multi-tenancy:** Chỉ cho phép xóa tài khoản nếu nó thuộc tổ chức của người dùng hiện tại.
    
    **Lưu ý:** Đây là soft delete - đặt is_active=False thay vì xóa khỏi cơ sở dữ liệu.
    
    Tham số đường dẫn:
    - account_id: ID tài khoản cần xóa
    
    Nâng cao:
    - 404: Tài khoản không tập hoặc không thuộc tổ chức hiện tại
    """
    await service.delete_account(
        db=db,
        account_id=account_id,
        org_id=current_user.org_id,
    )
    return None
