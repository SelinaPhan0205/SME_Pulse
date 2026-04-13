"""Bộ định tuyến FastAPI cho Khách hàng và Nhà cung cấp - Các điểm cuối API REST."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.core import User
from app.modules.auth.dependencies import get_current_user
from app.modules.partners import service
from app.schema.core import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    PaginatedCustomersResponse,
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    PaginatedSuppliersResponse,
)

logger = logging.getLogger(__name__)


# ============================================================
# ROUTER KHÁCH HÀNG
# ============================================================

customers_router = APIRouter(prefix="/customers", tags=["Customers"])


@customers_router.get(
    "/",
    response_model=PaginatedCustomersResponse,
    summary="Liệt kê khách hàng",
    description="Lấy danh sách phân trang khách hàng cho tổ chức hiện tại"
)
async def list_customers(
    skip: int = Query(0, ge=0, description="Số bản ghi cần bỏ qua"),
    limit: int = Query(100, ge=1, le=500, description="Kết quả tối đa trả về"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái hoạt động"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Liệt kê tất cả khách hàng cho tổ chức hiện tại.
    
    **Đa thuê:** Tự động lọc theo org_id của người dùng hiện tại.
    
    Query Parameters:
    - skip: Offset phân trang (mặc định: 0)
    - limit: Kết quả tối đa (mặc định: 100, tối đa: 500)
    - is_active: Lọc hoạt động/không hoạt động (tùy chọn)
    
    Trả lại:
    - Danh sách khách hàng được phân trang kèm tổng số
    """
    customers, total = await service.get_customers(
        db=db,
        org_id=current_user.org_id,  # Bộ lọc đa thuê
        skip=skip,
        limit=limit,
        is_active=is_active,
    )
    
    return PaginatedCustomersResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=customers,
    )


@customers_router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Lấy khách hàng theo ID",
    description="Truy xuất chi tiết khách hàng duy nhất"
)
async def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy khách hàng theo ID.
    
    **Đa thuê:** Chỉ trả lại khách hàng nếu nó thuộc tổ chức của người dùng hiện tại.
    
    Path Parameters:
    - customer_id: ID khách hàng
    
    Tăng:
    - 404: Khách hàng không được tìm thấy hoặc không thuộc tổ chức hiện tại
    """
    customer = await service.get_customer(
        db=db,
        customer_id=customer_id,
        org_id=current_user.org_id,  # Bảo vệ đa thuê
    )
    return customer


@customers_router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo khách hàng",
    description="Tạo khách hàng mới cho tổ chức hiện tại"
)
async def create_customer(
    schema: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo khách hàng mới.
    
    **Đa thuê:** Khách hàng được tự động gán cho tổ chức của người dùng hiện tại.
    
    **Quy tắc kinh doanh:**
    - Mã khách hàng phải duy nhất trong tổ chức (nếu cung cấp)
    - org_id được tiêm từ xác thực, KHÔNG từ thân yêu cầu
    
    Thân yêu cầu:
    - name: Tên khách hàng (bắt buộc)
    - code: Mã duy nhất trong org (tùy chọn)
    - tax_code, email, phone, address: Thông tin liên hệ (tùy chọn)
    - credit_term: Ngày (mặc định: 30)
    - is_active: Trạng thái hoạt động (mặc định: true)
    
    Tăng:
    - 400: Mã khách hàng trùng lặp
    """
    customer = await service.create_customer(
        db=db,
        schema=schema,
        org_id=current_user.org_id,  # Tiêm org_id từ xác thực
    )
    return customer


@customers_router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Cập nhật khách hàng",
    description="Cập nhật khách hàng hiện có"
)
async def update_customer(
    customer_id: int,
    schema: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật khách hàng.
    
    **Đa thuê:** Chỉ cho phép cập nhật khách hàng nếu nó thuộc tổ chức của người dùng hiện tại.
    
    **Quy tắc kinh doanh:**
    - Tất cả các trường là tùy chọn (cập nhật một phần)
    - Mã phải vẫn duy nhất trong tổ chức (nếu thay đổi)
    
    Tham số đường dẫn:
    - customer_id: ID khách hàng cần cập nhật
    
    Thân yêu cầu:
    - Bất kỳ trường CustomerUpdate nào (tất cả tùy chọn)
    
    Tăng:
    - 404: Khách hàng không được tìm thấy hoặc không thuộc tổ chức hiện tại
    - 400: Mã khách hàng trùng lặp
    """
    customer = await service.update_customer(
        db=db,
        customer_id=customer_id,
        schema=schema,
        org_id=current_user.org_id,  # Bảo vệ đa thuê
    )
    return customer


@customers_router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa khách hàng",
    description="Xóa mềm khách hàng (đặt is_active=False)"
)
async def delete_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Xóa khách hàng (xóa mềm).
    
    **Đa thuê:** Chỉ cho phép xóa khách hàng nếu nó thuộc tổ chức của người dùng hiện tại.
    
    **Ghi chú:** Đây là xóa mềm - đặt is_active=False thay vì xóa khỏi cơ sở dữ liệu.
    
    Tham số đường dẫn:
    - customer_id: ID khách hàng cần xóa
    
    Tăng:
    - 404: Khách hàng không được tìm thấy hoặc không thuộc tổ chức hiện tại
    """
    await service.delete_customer(
        db=db,
        customer_id=customer_id,
        org_id=current_user.org_id,  # Bảo vệ đa thuê
    )
    return None


# ============================================================
# ROUTER NHÀ CUNG CẤP
# ============================================================

suppliers_router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@suppliers_router.get(
    "/",
    response_model=PaginatedSuppliersResponse,
    summary="Liệt kê nhà cung cấp",
    description="Lấy danh sách phân trang nhà cung cấp cho tổ chức hiện tại"
)
async def list_suppliers(
    skip: int = Query(0, ge=0, description="Số bản ghi cần bỏ qua"),
    limit: int = Query(100, ge=1, le=500, description="Kết quả tối đa trả về"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái hoạt động"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Liệt kê tất cả nhà cung cấp cho tổ chức hiện tại.
    
    **Đa thuê:** Tự động lọc theo org_id của người dùng hiện tại.
    
    Tham số truy vấn:
    - skip: Offset phân trang (mặc định: 0)
    - limit: Kết quả tối đa (mặc định: 100, tối đa: 500)
    - is_active: Lọc hoạt động/không hoạt động (tùy chọn)
    
    Trả lại:
    - Danh sách nhà cung cấp được phân trang kèm tổng số
    """
    suppliers, total = await service.get_suppliers(
        db=db,
        org_id=current_user.org_id,  # Bộ lọc đa thuê
        skip=skip,
        limit=limit,
        is_active=is_active,
    )
    
    return PaginatedSuppliersResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=suppliers,
    )


@suppliers_router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Lấy nhà cung cấp theo ID",
    description="Truy xuất chi tiết nhà cung cấp duy nhất"
)
async def get_supplier(
    supplier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy nhà cung cấp theo ID.
    
    **Đa thuê:** Chỉ trả lại nhà cung cấp nếu nó thuộc tổ chức của người dùng hiện tại.
    
    Tham số đường dẫn:
    - supplier_id: ID nhà cung cấp
    
    Tăng:
    - 404: Nhà cung cấp không được tìm thấy hoặc không thuộc tổ chức hiện tại
    """
    supplier = await service.get_supplier(
        db=db,
        supplier_id=supplier_id,
        org_id=current_user.org_id,  # Bảo vệ đa thuê
    )
    return supplier


@suppliers_router.post(
    "/",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo nhà cung cấp",
    description="Tạo nhà cung cấp mới cho tổ chức hiện tại"
)
async def create_supplier(
    schema: SupplierCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo nhà cung cấp mới.
    
    **Đa thuê:** Nhà cung cấp được tự động gán cho tổ chức của người dùng hiện tại.
    
    **Quy tắc kinh doanh:**
    - Mã nhà cung cấp phải duy nhất trong tổ chức (nếu cung cấp)
    - org_id được tiêm từ xác thực, KHÔNG từ thân yêu cầu
    
    Thân yêu cầu:
    - name: Tên nhà cung cấp (bắt buộc)
    - code: Mã duy nhất trong org (tùy chọn)
    - tax_code, email, phone, address: Thông tin liên hệ (tùy chọn)
    - payment_term: Ngày (mặc định: 30)
    - is_active: Trạng thái hoạt động (mặc định: true)
    
    Tăng:
    - 400: Mã nhà cung cấp trùng lặp
    """
    supplier = await service.create_supplier(
        db=db,
        schema=schema,
        org_id=current_user.org_id,  # Tiêm org_id từ xác thực
    )
    return supplier


@suppliers_router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Cập nhật nhà cung cấp",
    description="Cập nhật nhà cung cấp hiện có"
)
async def update_supplier(
    supplier_id: int,
    schema: SupplierUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật nhà cung cấp.
    
    **Đa thuê:** Chỉ cho phép cập nhật nhà cung cấp nếu nó thuộc tổ chức của người dùng hiện tại.
    
    **Quy tắc kinh doanh:**
    - Tất cả các trường là tùy chọn (cập nhật một phần)
    - Mã phải vẫn duy nhất trong tổ chức (nếu thay đổi)
    
    Tham số đường dẫn:
    - supplier_id: ID nhà cung cấp cần cập nhật
    
    Thân yêu cầu:
    - Bất kỳ trường SupplierUpdate nào (tất cả tùy chọn)
    
    Tăng:
    - 404: Nhà cung cấp không được tìm thấy hoặc không thuộc tổ chức hiện tại
    - 400: Mã nhà cung cấp trùng lặp
    """
    supplier = await service.update_supplier(
        db=db,
        supplier_id=supplier_id,
        schema=schema,
        org_id=current_user.org_id,  # Bảo vệ đa thuê
    )
    return supplier


@suppliers_router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa nhà cung cấp",
    description="Xóa mềm nhà cung cấp (đặt is_active=False)"
)
async def delete_supplier(
    supplier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Xóa nhà cung cấp (xóa mềm).
    
    **Đa thuê:** Chỉ cho phép xóa nhà cung cấp nếu nó thuộc tổ chức của người dùng hiện tại.
    
    **Ghi chú:** Đây là xóa mềm - đặt is_active=False thay vì xóa khỏi cơ sở dữ liệu.
    
    Tham số đường dẫn:
    - supplier_id: ID nhà cung cấp cần xóa
    
    Tăng:
    - 404: Nhà cung cấp không được tìm thấy hoặc không thuộc tổ chức hiện tại
    """
    await service.delete_supplier(
        db=db,
        supplier_id=supplier_id,
        org_id=current_user.org_id,  # Bảo vệ đa thuê
    )
    return None
