"""Router Tài chính - Hóa đơn AR/AP và Thanh toán."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, status

from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import get_current_user, requires_roles
from app.models.core import User
from app.schema.finance import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoicePost,
    InvoiceResponse,
    PaginatedInvoicesResponse,
    InvoiceBulkImportRequest,
    InvoiceBulkImportResponse,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaginatedPaymentsResponse,
)
from app.modules.finance.services import invoice_service, payment_service


router = APIRouter()


# ==================== AR INVOICES ====================

@router.get("/invoices", response_model=PaginatedInvoicesResponse)
async def list_invoices(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liệt kê hóa đơn AR có lọc và phân trang.
    
    Query Parameters:
        - skip: Offset cho phân trang (mặc định: 0)
        - limit: Tối đa bản ghi trả về (mặc định: 100)
        - status: Lọc theo trạng thái hóa đơn (nháp, đã đăng, trả một phần, đã trả, quá hạn, đã hủy)
        - customer_id: Lọc theo ID khách hàng
        - date_from: Lọc theo issue_date >= date_from
        - date_to: Lọc theo issue_date <= date_to
    """
    invoices, total = await invoice_service.get_invoices(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        status=status,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
    )
    
    return PaginatedInvoicesResponse(
        items=[InvoiceResponse.model_validate(inv) for inv in invoices],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy một hóa đơn theo ID."""
    invoice = await invoice_service.get_invoice(
        db=db,
        invoice_id=invoice_id,
        org_id=current_user.org_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tạo hóa đơn AR mới ở trạng thái NHÁP.
    
    Hóa đơn mới luôn bắt đầu với:
    - status = "nháp"
    - paid_amount = 0
    """
    invoice = await invoice_service.create_invoice(
        db=db,
        schema=invoice_in,
        org_id=current_user.org_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_in: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật các trường hóa đơn (chỉ được phép ở trạng thái NHÁP).
    
    Tăng:
        400: Nếu hóa đơn đã được đăng
    """
    invoice = await invoice_service.update_invoice(
        db=db,
        invoice_id=invoice_id,
        schema=invoice_in,
        org_id=current_user.org_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.post("/invoices/{invoice_id}/post", response_model=InvoiceResponse)
async def post_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(requires_roles(["accountant", "admin", "owner"])),
):
    """Đăng hóa đơn (chuyển đổi NHÁP → ĐÃ ĐĂNG).
    
    **RBAC:** Chỉ Kế toán, Quản trị viên hoặc Chủ sở hữu mới có thể đăng hóa đơn.
    Thu ngân bị hạn chế không được đăng.
    
    Sau khi đăng, hóa đơn trở thành bất biến:
    - Không thể cập nhật
    - Không thể xóa
    - Có thể nhận các phân bổ thanh toán
    
    Tăng:
        403: Nếu vai trò người dùng không được phép (ví dụ: Thu ngân)
        400: Nếu hóa đơn đã được đăng hoặc có số tiền không hợp lệ
    """
    invoice = await invoice_service.post_invoice(
        db=db,
        invoice_id=invoice_id,
        org_id=current_user.org_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xóa hóa đơn (chỉ được phép ở trạng thái NHÁP).
    
    Tăng:
        400: Nếu hóa đơn đã được đăng
    """
    await invoice_service.delete_invoice(
        db=db,
        invoice_id=invoice_id,
        org_id=current_user.org_id,
    )
    return None


@router.post("/invoices/bulk-import", response_model=InvoiceBulkImportResponse)
async def bulk_import_invoices(
    import_request: InvoiceBulkImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(requires_roles(["accountant", "admin", "owner"])),
):
    """Nhập hàng loạt hóa đơn từ dữ liệu Excel/CSV.
    
    **RBAC:** Kế toán, Quản trị viên hoặc Chủ sở hữu có thể nhập hóa đơn.
    
    Request Body:
        - invoices: Danh sách các đối tượng hóa đơn (tối đa 100)
        - auto_post: Nếu True, hóa đơn sẽ được đăng tự động sau khi tạo
    
    Trả lại:
        Kết quả nhập với thành công/thất bại cho mỗi hóa đơn
    
    Ghi chú:
        - Duplicate invoice_no sẽ bị từ chối
        - Invalid customer_id sẽ gây ra lỗi
        - Cho phép nhập một phần (một số thành công, một số thất bại)
    """
    result = await invoice_service.bulk_import_invoices(
        db=db,
        invoices_data=import_request.invoices,
        org_id=current_user.org_id,
        auto_post=import_request.auto_post,
    )
    
    return InvoiceBulkImportResponse(**result)


# ==================== PAYMENTS ====================

@router.get("/payments", response_model=PaginatedPaymentsResponse)
async def list_payments(
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_id: Optional[int] = None,
    payment_method: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liệt kê các khoản thanh toán có phân trang và lọc.
    
    Query Parameters:
        - skip: Offset cho phân trang (mặc định: 0)
        - limit: Tối đa bản ghi trả về (mặc định: 100)
        - date_from: Lọc theo transaction_date >= date_from
        - date_to: Lọc theo transaction_date <= date_to
        - account_id: Lọc theo ID tài khoản
        - payment_method: Lọc theo phương thức thanh toán (tiền mặt, chuyển khoản, vietqr, thẻ)
    """
    payments, total = await payment_service.get_payments(
        db=db,
        org_id=current_user.org_id,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        payment_method=payment_method,
    )
    
    return PaginatedPaymentsResponse(
        items=[PaymentResponse.model_validate(pmt) for pmt in payments],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy một khoản thanh toán theo ID kèm phân bổ."""
    payment = await payment_service.get_payment(
        db=db,
        payment_id=payment_id,
        org_id=current_user.org_id,
    )
    return PaymentResponse.model_validate(payment)


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tạo thanh toán với phân bổ cho hóa đơn/phiếu.
    
    Endpoint này triển khai logic giao dịch NGUYÊN TỬ:
    - Tạo bản ghi thanh toán
    - Tạo bản ghi phân bổ
    - Cập nhật paid_amount của hóa đơn/phiếu
    - Cập nhật trạng thái hóa đơn/phiếu (trả một phần/đã trả)
    - Tất cả các thay đổi commit cùng nhau hoặc rollback khi có lỗi
    
    Quy tắc kinh doanh:
    - Chỉ có thể phân bổ cho hóa đơn/phiếu ĐÃ ĐĂNG (không phải NHÁP)
    - Số tiền phân bổ không được vượt quá số dư còn lại
    - Tổng phân bổ không được vượt quá số tiền thanh toán (được xác thực bằng schema)
    - Mỗi phân bổ phải có ar_invoice_id HOẶC ap_bill_id (loại trừ)
    
    Tăng:
        400: Nếu xác thực thất bại (tài khoản, hóa đơn, số tiền phân bổ)
    """
    payment = await payment_service.create_payment_with_allocations(
        db=db,
        schema=payment_in,
        org_id=current_user.org_id,
    )
    return PaymentResponse.model_validate(payment)


@router.put("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_in: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật siêu dữ liệu thanh toán (chỉ ghi chú và reference_code).
    
    TRƯỜNG BẤT BIẾN (không thể sửa đổi sau khi tạo):
    - amount: Đường dò kiểm toán yêu cầu số tiền thanh toán gốc được khóa
    - transaction_date: Dấu thời gian phải vẫn bất biến
    - account_id: Tài khoản nguồn không thể thay đổi (phá vỡ chuỗi FK)
    - allocations: Không thể sửa đổi phân bổ hiện có (tạo thanh toán mới hoặc bỏ phân bổ riêng)
    
    CÓ THỂ CẬP NHẬT (chỉ siêu dữ liệu):
    - notes: Thêm/cập nhật ghi chú thanh toán (ví dụ: lý do phân bổ bị trễ)
    - reference_code: Thêm/cập nhật mã giao dịch ngân hàng/tài liệu tham khảo
    
    Trường hợp sử dụng:
    - Thanh toán được tạo nhưng ngân hàng cung cấp mã giao dịch sau → cập nhật reference_code
    - Thanh toán cần ghi chú để kiểm toán → cập nhật notes
    
    Tăng:
        404: Nếu thanh toán không được tìm thấy
        400: Nếu cố gắng cập nhật các trường bất biến (sẽ bị từ chối trong service)
    """
    payment = await payment_service.update_payment(
        db=db,
        payment_id=payment_id,
        org_id=current_user.org_id,
        schema=payment_in,
    )
    return PaymentResponse.model_validate(payment)

