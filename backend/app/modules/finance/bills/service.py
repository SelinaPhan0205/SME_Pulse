"""Lớp Dịch vụ AP Bill - Logic kinh doanh cho Hóa đơn (phản chiếu của Hóa đơn AR)."""

import logging
from typing import Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import date

from app.models.finance import APBill
from app.models.core import Supplier
from app.schema.finance.bill import BillCreate, BillUpdate

logger = logging.getLogger(__name__)


async def get_bills(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[list[APBill], int]:
    """
    Lấy danh sách hóa đơn phân trang cho một tổ chức.
    
    Tham số:
        db: Database session
        org_id: ID tổ chức (CRITICAL cho multi-tenancy)
        skip: Số bản ghi cần bỏ qua
        limit: Số bản ghi tối đa trả về
        status: Lọc theo trạng thái (draft, posted, partial, paid, cancelled)
        supplier_id: Lọc theo ID nhà cung cấp
        date_from: Lọc theo issue_date >= date_from
        date_to: Lọc theo issue_date <= date_to
    
    Trả về:
        Tuple (danh sách hóa đơn, tổng số)
    """
    # Xây dựng bộ lọc
    filters = [APBill.org_id == org_id]
    
    if status:
        filters.append(APBill.status == status)
    
    if supplier_id:
        filters.append(APBill.supplier_id == supplier_id)
    
    if date_from:
        filters.append(APBill.issue_date >= date_from)
    
    if date_to:
        filters.append(APBill.issue_date <= date_to)
    
    # Đếm tổng số
    count_stmt = select(func.count()).select_from(APBill).where(and_(*filters))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Lây danh sách với phân trang
    stmt = (
        select(APBill)
        .where(and_(*filters))
        .options(selectinload(APBill.supplier))
        .order_by(APBill.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    bills = result.unique().scalars().all()
    
    logger.info(f"Retrieved {len(bills)} bills for org_id={org_id}")
    return list(bills), total


async def get_bill(
    db: AsyncSession,
    bill_id: int,
    org_id: int,
) -> APBill:
    """
    Lấy một hóa đơn đơn lẻ theo ID.
    
    CRITICAL: Luôn lọc theo org_id để ngăn chặn cross-tenant access.
    
    Tham số:
        db: Database session
        bill_id: ID hóa đơn
        org_id: ID tổ chức
    
    Trả về:
        APBill object với supplier được load
    
    Nâng cao:
        HTTPException 404: Hóa đơn không tìm thấy
    """
    stmt = (
        select(APBill)
        .where(and_(APBill.id == bill_id, APBill.org_id == org_id))
        .options(selectinload(APBill.supplier))
    )
    result = await db.execute(stmt)
    bill = result.unique().scalar_one_or_none()
    
    if not bill:
        logger.warning(f"Bill {bill_id} not found for org_id={org_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found"
        )
    
    return bill


async def create_bill(
    db: AsyncSession,
    schema: BillCreate,
    org_id: int,
) -> APBill:
    """
    Tạo hóa đơn mới ở trạng thái DRAFT.
    
    Quy tắc kinh doanh:
    - bill_no nên độc lập trong tổ chức
    - Nhà cung cấp phải tồn tại và thuộc tổ chức
    - due_date phải >= issue_date
    - Trạng thái mặc định là 'draft', paid_amount là 0
    
    Tham số:
        db: Database session
        schema: BillCreate schema
        org_id: ID tổ chức
    
    Trả về:
        Hóa đơn được tạo
    
    Nâng cao:
        HTTPException 400: Lỗi xác thực (bill_no trùng lặp, nhà cung cấp không hợp lệ, ngày không hợp lệ)
    """
    # Xác thực bill_no độc nhất
    existing_stmt = select(APBill).where(
        and_(APBill.bill_no == schema.bill_no, APBill.org_id == org_id)
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bill number '{schema.bill_no}' already exists"
        )
    
    # Xác thực nhà cung cấp tồn tại
    supplier_stmt = select(Supplier).where(
        and_(Supplier.id == schema.supplier_id, Supplier.org_id == org_id)
    )
    supplier_result = await db.execute(supplier_stmt)
    if not supplier_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supplier {schema.supplier_id} not found"
        )
    
    # Xác thực ngày
    if schema.due_date < schema.issue_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Due date must be >= issue date"
        )
    
    # Tạo hóa đơn
    bill = APBill(
        bill_no=schema.bill_no,
        supplier_id=schema.supplier_id,
        issue_date=schema.issue_date,
        due_date=schema.due_date,
        total_amount=schema.total_amount,
        paid_amount=0,
        status="draft",
        notes=schema.notes,
        org_id=org_id,
    )
    
    db.add(bill)
    await db.commit()
    await db.refresh(bill)
    
    # Tải lại với supplier được load
    await db.execute(
        select(APBill)
        .where(APBill.id == bill.id)
        .options(selectinload(APBill.supplier))
    )
    
    logger.info(f"Created bill {bill.id} ({bill.bill_no}) for org_id={org_id}")
    return bill


async def update_bill(
    db: AsyncSession,
    bill_id: int,
    schema: BillUpdate,
    org_id: int,
) -> APBill:
    """
    Cập nhật hóa đơn (chỉ được phép ở trạng thái DRAFT).
    
    Quy tắc kinh doanh:
    - Chỉ có thể cập nhật hóa đơn draft
    - Không thể thay đổi hóa đơn sau khi được ghi
    
    Tham số:
        db: Database session
        bill_id: ID hóa đơn cần cập nhật
        schema: BillUpdate schema
        org_id: ID tổ chức
    
    Trả về:
        Hóa đơn được cập nhật
    
    Nâng cao:
        HTTPException 400: Hóa đơn đã được ghi
        HTTPException 404: Hóa đơn không tìm thấy
    """
    # Lấy hóa đơn
    bill = await get_bill(db, bill_id, org_id)
    
    # Kiểm tra xem hóa đơn có ở trạng thái nháp không
    if bill.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update bills in draft status"
        )
    
    # Cập nhật các trường
    if schema.supplier_id is not None:
        # Xác thực nhà cung cấp tồn tại
        supplier_stmt = select(Supplier).where(
            and_(Supplier.id == schema.supplier_id, Supplier.org_id == org_id)
        )
        supplier_result = await db.execute(supplier_stmt)
        if not supplier_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier {schema.supplier_id} not found"
            )
        bill.supplier_id = schema.supplier_id
    
    if schema.issue_date is not None:
        bill.issue_date = schema.issue_date
    
    if schema.due_date is not None:
        bill.due_date = schema.due_date
    
    if schema.total_amount is not None:
        bill.total_amount = schema.total_amount
    
    if schema.notes is not None:
        bill.notes = schema.notes
    
    # Xac thực ngày
    if bill.due_date < bill.issue_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Due date must be >= issue date"
        )
    
    await db.commit()
    await db.refresh(bill)
    
    logger.info(f"Updated bill {bill.id}")
    return bill


async def post_bill(
    db: AsyncSession,
    bill_id: int,
    org_id: int,
) -> APBill:
    """
    Ghi hóa đơn (chuyển DRAFT thành POSTED).
    
    Sau khi ghi, hóa đơn trở thành bất biến và có thể nhận phân bổ thanh toán.
    
    Quy tắc kinh doanh:
    - Chỉ có thể ghi hóa đơn draft
    - total_amount phải > 0
    
    Tham số:
        db: Database session
        bill_id: ID hóa đơn
        org_id: ID tổ chức
    
    Trả về:
        Hóa đơn được ghi
    
    Nâng cao:
        HTTPException 400: Hóa đơn đã được ghi hoặc số tiền không hợp lệ
        HTTPException 404: Hóa đơn không tìm thấy
    """
    # Lấy hóa đơn
    bill = await get_bill(db, bill_id, org_id)
    
    # Xác thực trạng thái draft
    if bill.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill already posted"
        )
    
    # Xác thực tổng số tiền
    if bill.total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total amount must be greater than 0"
        )
    
    # Chuyển trạng thái thành posted
    bill.status = "posted"
    
    await db.commit()
    await db.refresh(bill)
    
    logger.info(f"Posted bill {bill.id}")
    return bill


async def delete_bill(
    db: AsyncSession,
    bill_id: int,
    org_id: int,
) -> None:
    """
    Xóa hóa đơn (chỉ được phép ở trạng thái DRAFT).
    
    Quy tắc kinh doanh:
    - Chỉ có thể xóa hóa đơn draft
    - Đặt trạng thái thành 'cancelled' (soft delete)
    
    Tham số:
        db: Database session
        bill_id: ID hóa đơn
        org_id: ID tổ chức
    
    Nâng cao:
        HTTPException 400: Hóa đơn đã được ghi
        HTTPException 404: Hóa đơn không tìm thấy
    """
    # Lấy hóa đơn
    bill = await get_bill(db, bill_id, org_id)
    
    # Kiểm tra xem hóa đơn có ở trạng thái nháp không
    if bill.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete bills in draft status"
        )
    
    # Đặt trạng thái thành cancelled
    bill.status = "cancelled"
    
    await db.commit()
    
    logger.info(f"Deleted bill {bill.id} (soft delete)")
