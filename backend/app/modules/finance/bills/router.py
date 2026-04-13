"""Router Hóa đơn AP - REST API endpoints cho Hóa đơn (Quản lý Công nợ Phải trả)."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.db.session import get_db
from app.models.core import User
from app.modules.auth.dependencies import get_current_user, requires_roles
from app.modules.finance.bills import service
from app.schema.finance.bill import (
    BillCreate,
    BillUpdate,
    BillResponse,
    PaginatedBillsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bills", tags=["AP Bills"])


@router.get("/", response_model=PaginatedBillsResponse)
async def list_bills(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liệt kê hóa đơn AP với lọc và phân trang.
    
    Tham số truy vấn:
    - skip: Độ lệch phân trang (mặc định: 0)
    - limit: Số bản ghi tối đa trả về (mặc định: 100)
    - status: Lọc theo trạng thái hóa đơn (draft, posted, partial, paid, cancelled)
    - supplier_id: Lọc theo ID nhà cung cấp
    - date_from: Lọc theo issue_date >= date_from
    - date_to: Lọc theo issue_date <= date_to
    """
    bills, total = await service.get_bills(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        status=status,
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
    )
    
    return PaginatedBillsResponse(
        items=[BillResponse.model_validate(bill) for bill in bills],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{bill_id}", response_model=BillResponse)
async def get_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy một hóa đơn đơn lẻ theo ID."""
    bill = await service.get_bill(
        db=db,
        bill_id=bill_id,
        org_id=current_user.org_id,
    )
    return BillResponse.model_validate(bill)


@router.post("/", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
async def create_bill(
    bill_in: BillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tạo hóa đơn AP mới ở trạng thái DRAFT.
    
    Hóa đơn mới luôn bắt đầu với:
    - status = "draft"
    - paid_amount = 0
    """
    bill = await service.create_bill(
        db=db,
        schema=bill_in,
        org_id=current_user.org_id,
    )
    return BillResponse.model_validate(bill)


@router.put("/{bill_id}", response_model=BillResponse)
async def update_bill(
    bill_id: int,
    bill_in: BillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cập nhật trường hóa đơn (chỉ được phép ở trạng thái DRAFT).
    
    Nâng cao:
    - 400: Nếu hóa đơn đã được ghi
    """
    bill = await service.update_bill(
        db=db,
        bill_id=bill_id,
        schema=bill_in,
        org_id=current_user.org_id,
    )
    return BillResponse.model_validate(bill)


@router.post("/{bill_id}/post", response_model=BillResponse)
async def post_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(requires_roles(["accountant", "admin", "owner"])),
):
    """
    Ghi hóa đơn (chuyển DRAFT → POSTED).
    
    Sau khi ghi, hóa đơn trở thành bất biến:
    - Không thể cập nhật
    - Không thể xóa
    - Có thể nhận phân bổ thanh toán
    
    Nâng cao:
    - 400: Nếu hóa đơn đã được ghi hoặc có số tiền không hợp lệ
    """
    bill = await service.post_bill(
        db=db,
        bill_id=bill_id,
        org_id=current_user.org_id,
    )
    return BillResponse.model_validate(bill)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Xóa hóa đơn (chỉ được phép ở trạng thái DRAFT).
    
    Nâng cao:
    - 400: Nếu hóa đơn đã được ghi
    """
    await service.delete_bill(
        db=db,
        bill_id=bill_id,
        org_id=current_user.org_id,
    )
    return None
