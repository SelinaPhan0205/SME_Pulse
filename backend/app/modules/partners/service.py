"""Lớp dịch vụ cho Khách hàng và Nhà cung cấp - Logic kinh doanh với Đa thuê."""

import logging
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.core import Customer, Supplier
from app.schema.core import (
    CustomerCreate,
    CustomerUpdate,
    SupplierCreate,
    SupplierUpdate,
)

logger = logging.getLogger(__name__)


# ============================================================
# DỊCH VỤ KHÁCH HÀNG
# ============================================================

async def get_customers(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> tuple[list[Customer], int]:
    """
    Lấy danh sách khách hàng được phân trang cho một tổ chức.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        org_id: ID tổ chức (QUAN TRỌNG để đa thuê)
        skip: Số bản ghi cần bỏ qua
        limit: Tối đa bản ghi trả về
        is_active: Lọc theo trạng thái hoạt động (tùy chọn)
    
    Trả lại:
        Tuple của (danh sách khách hàng, tổng số)
    """
    # Xây dựng câu truy vấn cơ sở với bộ lọc đa thuê
    base_filter = Customer.org_id == org_id
    if is_active is not None:
        base_filter = and_(base_filter, Customer.is_active == is_active)
    
    # Đếm tổng số
    count_stmt = select(func.count()).select_from(Customer).where(base_filter)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Lấy dữ liệu được phân trang
    stmt = (
        select(Customer)
        .where(base_filter)
        .order_by(Customer.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    customers = result.scalars().all()
    
    logger.info(f"Retrieved {len(customers)} customers for org_id={org_id}")
    return list(customers), total


async def get_customer(
    db: AsyncSession,
    customer_id: int,
    org_id: int,
) -> Customer:
    """
    Lấy một khách hàng theo ID.
    
    QUAN TRỌNG: Luôn lọc theo org_id để ngăn chặn truy cập xuyên thuê.
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        customer_id: ID khách hàng
        org_id: ID tổ chức
    
    Trả lại:
        Đối tượng khách hàng
    
    Tăng:
        HTTPException 404: Khách hàng không được tìm thấy
    """
    stmt = select(Customer).where(
        and_(
            Customer.id == customer_id,
            Customer.org_id == org_id  # Bảo vệ đa thuê
        )
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()
    
    if not customer:
        logger.warning(f"Customer {customer_id} not found for org_id={org_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    return customer


async def create_customer(
    db: AsyncSession,
    schema: CustomerCreate,
    org_id: int,
) -> Customer:
    """
    Tạo khách hàng mới.
    
    Quy tắc kinh doanh:
    - Mã khách hàng phải duy nhất trong tổ chức (nếu cung cấp)
    - org_id được TIÊM từ current_user, KHÔNG từ thân yêu cầu
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        schema: Dữ liệu tạo khách hàng
        org_id: ID tổ chức (được tiêm từ xác thực)
    
    Trả lại:
        Khách hàng được tạo
    
    Tăng:
        HTTPException 400: Mã khách hàng trùng lặp
    """
    # Kiểm tra mã trùng lặp trong tổ chức
    if schema.code:
        stmt = select(Customer).where(
            and_(
                Customer.code == schema.code,
                Customer.org_id == org_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(
                f"Duplicate customer code '{schema.code}' for org_id={org_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer with code '{schema.code}' already exists"
            )
    
    # Tạo khách hàng - tiêm org_id
    customer = Customer(
        **schema.model_dump(),
        org_id=org_id  # QUAN TRỌNG: Tiêm từ xác thực, không từ yêu cầu
    )
    
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    
    logger.info(f"Created customer {customer.id} for org_id={org_id}")
    return customer


async def update_customer(
    db: AsyncSession,
    customer_id: int,
    schema: CustomerUpdate,
    org_id: int,
) -> Customer:
    """
    Cập nhật khách hàng hiện có.
    
    Quy tắc kinh doanh:
    - Khách hàng phải thuộc tổ chức hiện tại
    - Mã phải duy nhất trong tổ chức (nếu thay đổi)
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        customer_id: ID khách hàng cần cập nhật
        schema: Dữ liệu cập nhật (một phần)
        org_id: ID tổ chức
    
    Trả lại:
        Khách hàng được cập nhật
    
    Tăng:
        HTTPException 404: Khách hàng không được tìm thấy
        HTTPException 400: Mã trùng lặp
    """
    # Lấy khách hàng hiện có (với kiểm tra đa thuê)
    customer = await get_customer(db, customer_id, org_id)
    
    # Kiểm tra mã trùng lặp nếu mã đang được cập nhật
    update_data = schema.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] != customer.code:
        stmt = select(Customer).where(
            and_(
                Customer.code == update_data["code"],
                Customer.org_id == org_id,
                Customer.id != customer_id  # Bỏ qua khách hàng hiện tại
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer with code '{update_data['code']}' already exists"
            )
    
    # Cập nhật các trường
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    await db.commit()
    await db.refresh(customer)
    
    logger.info(f"Updated customer {customer_id} for org_id={org_id}")
    return customer


async def delete_customer(
    db: AsyncSession,
    customer_id: int,
    org_id: int,
) -> None:
    """
    Xóa khách hàng (xóa mềm bằng cách đặt is_active=False).
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        customer_id: ID khách hàng
        org_id: ID tổ chức
    
    Tăng:
        HTTPException 404: Khách hàng không được tìm thấy
    """
    customer = await get_customer(db, customer_id, org_id)
    
    # Xóa mềm
    customer.is_active = False
    await db.commit()
    
    logger.info(f"Deleted (soft) customer {customer_id} for org_id={org_id}")


# ============================================================
# DỊCH VỤ NHÀ CUNG CẤP
# ============================================================

async def get_suppliers(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> tuple[list[Supplier], int]:
    """
    Lấy danh sách nhà cung cấp được phân trang cho một tổ chức.
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        org_id: ID tổ chức (QUAN TRỌNG cho đa thuê)
        skip: Số bản ghi cần bỏ qua
        limit: Tối đa bản ghi trả về
        is_active: Lọc theo trạng thái hoạt động (tùy chọn)
    
    Trả lại:
        Tuple của (danh sách nhà cung cấp, tổng số)
    """
    # Xây dựng câu truy vấn cơ sở với bộ lọc đa thuê
    base_filter = Supplier.org_id == org_id
    if is_active is not None:
        base_filter = and_(base_filter, Supplier.is_active == is_active)
    
    # Đếm tổng số
    count_stmt = select(func.count()).select_from(Supplier).where(base_filter)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Lấy dữ liệu được phân trang
    stmt = (
        select(Supplier)
        .where(base_filter)
        .order_by(Supplier.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    suppliers = result.scalars().all()
    
    logger.info(f"Retrieved {len(suppliers)} suppliers for org_id={org_id}")
    return list(suppliers), total


async def get_supplier(
    db: AsyncSession,
    supplier_id: int,
    org_id: int,
) -> Supplier:
    """
    Lấy một nhà cung cấp theo ID.
    
    QUAN TRỌNG: Luôn lọc theo org_id để ngăn chặn truy cập xuyên thuê.
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        supplier_id: ID nhà cung cấp
        org_id: ID tổ chức
    
    Trả lại:
        Đối tượng nhà cung cấp
    
    Tăng:
        HTTPException 404: Nhà cung cấp không được tìm thấy
    """
    stmt = select(Supplier).where(
        and_(
            Supplier.id == supplier_id,
            Supplier.org_id == org_id  # Bảo vệ đa thuê
        )
    )
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        logger.warning(f"Supplier {supplier_id} not found for org_id={org_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with ID {supplier_id} not found"
        )
    
    return supplier


async def create_supplier(
    db: AsyncSession,
    schema: SupplierCreate,
    org_id: int,
) -> Supplier:
    """
    Tạo nhà cung cấp mới.
    
    Quy tắc kinh doanh:
    - Mã nhà cung cấp phải duy nhất trong tổ chức (nếu cung cấp)
    - org_id được TIÊM từ current_user, KHÔNG từ thân yêu cầu
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        schema: Dữ liệu tạo nhà cung cấp
        org_id: ID tổ chức (được tiêm từ xác thực)
    
    Trả lại:
        Nhà cung cấp được tạo
    
    Tăng:
        HTTPException 400: Mã nhà cung cấp trùng lặp
    """
    # Kiểm tra mã trùng lặp trong tổ chức
    if schema.code:
        stmt = select(Supplier).where(
            and_(
                Supplier.code == schema.code,
                Supplier.org_id == org_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(
                f"Duplicate supplier code '{schema.code}' for org_id={org_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with code '{schema.code}' already exists"
            )
    
    # Tạo nhà cung cấp - tiêm org_id
    supplier = Supplier(
        **schema.model_dump(),
        org_id=org_id  # QUAN TRỌNG: Tiêm từ xác thực, không từ yêu cầu
    )
    
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    
    logger.info(f"Created supplier {supplier.id} for org_id={org_id}")
    return supplier


async def update_supplier(
    db: AsyncSession,
    supplier_id: int,
    schema: SupplierUpdate,
    org_id: int,
) -> Supplier:
    """
    Cập nhật nhà cung cấp hiện có.
    
    Quy tắc kinh doanh:
    - Nhà cung cấp phải thuộc tổ chức hiện tại
    - Mã phải duy nhất trong tổ chức (nếu thay đổi)
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        supplier_id: ID nhà cung cấp cần cập nhật
        schema: Dữ liệu cập nhật (một phần)
        org_id: ID tổ chức
    
    Trả lại:
        Nhà cung cấp được cập nhật
    
    Tăng:
        HTTPException 404: Nhà cung cấp không được tìm thấy
        HTTPException 400: Mã trùng lặp
    """
    # Lấy nhà cung cấp hiện có (với kiểm tra đa thuê)
    supplier = await get_supplier(db, supplier_id, org_id)
    
    # Kiểm tra mã trùng lặp nếu mã đang được cập nhật
    update_data = schema.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] != supplier.code:
        stmt = select(Supplier).where(
            and_(
                Supplier.code == update_data["code"],
                Supplier.org_id == org_id,
                Supplier.id != supplier_id  # Bỏ qua nhà cung cấp hiện tại
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with code '{update_data['code']}' already exists"
            )
    
    # Cập nhật các trường
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    await db.commit()
    await db.refresh(supplier)
    
    logger.info(f"Updated supplier {supplier_id} for org_id={org_id}")
    return supplier


async def delete_supplier(
    db: AsyncSession,
    supplier_id: int,
    org_id: int,
) -> None:
    """
    Xóa nhà cung cấp (xóa mềm bằng cách đặt is_active=False).
    
    Tham số:
        db: Phiên cơ sở dữ liệu
        supplier_id: ID nhà cung cấp
        org_id: ID tổ chức
    
    Tăng:
        HTTPException 404: Nhà cung cấp không được tìm thấy
    """
    supplier = await get_supplier(db, supplier_id, org_id)
    
    # Xóa mềm
    supplier.is_active = False
    await db.commit()
    
    logger.info(f"Deleted (soft) supplier {supplier_id} for org_id={org_id}")
