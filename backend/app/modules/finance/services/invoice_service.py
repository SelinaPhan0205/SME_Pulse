"""Service Hóa đơn - Logic kinh doanh cho quản lý Hóa đơn AR."""

from datetime import date
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import ARInvoice
from app.models.core import Customer
from app.schema.finance import InvoiceCreate, InvoiceUpdate, InvoicePost


async def get_invoices(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[Sequence[ARInvoice], int]:
    """Lấy danh sách hóa đơn AR có lọc và phân trang.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        org_id: ID tổ chức từ JWT
        skip: Offset cho phân trang
        limit: Tối đa bản ghi trả về
        status: Lọc theo trạng thái hóa đơn
        customer_id: Lọc theo khách hàng
        date_from: Lọc theo issue_date >= date_from
        date_to: Lọc theo issue_date <= date_to
    
    Trả lại:
        Tuple của (danh sách hóa đơn, tổng số)
    """
    # Xây dựng truy vấn cơ bản
    query = select(ARInvoice).where(ARInvoice.org_id == org_id)
    count_query = select(func.count()).select_from(ARInvoice).where(ARInvoice.org_id == org_id)
    
    # Áp dụng bộ lọc
    if status:
        query = query.where(ARInvoice.status == status)
        count_query = count_query.where(ARInvoice.status == status)
    
    if customer_id:
        query = query.where(ARInvoice.customer_id == customer_id)
        count_query = count_query.where(ARInvoice.customer_id == customer_id)
    
    if date_from:
        query = query.where(ARInvoice.issue_date >= date_from)
        count_query = count_query.where(ARInvoice.issue_date >= date_from)
    
    if date_to:
        query = query.where(ARInvoice.issue_date <= date_to)
        count_query = count_query.where(ARInvoice.issue_date <= date_to)
    
    # Thêm phân trang và sắp xếp
    query = query.offset(skip).limit(limit).order_by(ARInvoice.issue_date.desc())
    
    # Thực thi truy vấn
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    return invoices, total


async def get_invoice(
    db: AsyncSession,
    invoice_id: int,
    org_id: int,
) -> ARInvoice:
    """Lấy một hóa đơn theo ID.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        invoice_id: ID hóa đơn
        org_id: ID tổ chức từ JWT
    
    Trả lại:
        Instance ARInvoice
    
    Tăng:
        HTTPException: 404 nếu không tìm thấy hoặc thuộc org khác
    """
    query = select(ARInvoice).where(
        ARInvoice.id == invoice_id,
        ARInvoice.org_id == org_id,
    )
    result = await db.execute(query)
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )
    
    return invoice


async def create_invoice(
    db: AsyncSession,
    schema: InvoiceCreate,
    org_id: int,
) -> ARInvoice:
    """Tạo hóa đơn AR mới ở trạng thái NHÁP.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        schema: Dữ liệu tạo hóa đơn
        org_id: ID tổ chức từ JWT
    
    Trả lại:
        Instance ARInvoice được tạo
    
    Tăng:
        HTTPException: 400 nếu khách hàng không tồn tại hoặc thuộc org khác
    """
    # Xác thực khách hàng tồn tại và thuộc tổ chức
    customer_query = select(Customer).where(
        Customer.id == schema.customer_id,
        Customer.org_id == org_id,
    )
    customer_result = await db.execute(customer_query)
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer {schema.customer_id} not found in your organization",
        )
    
    # Tạo hóa đơn
    invoice = ARInvoice(
        **schema.model_dump(),
        org_id=org_id,
        status="draft",
        paid_amount=0,  # lúc tạo luôn đặt paid_amount = 0
    )
    
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


async def update_invoice(
    db: AsyncSession,
    invoice_id: int,
    schema: InvoiceUpdate,
    org_id: int,
) -> ARInvoice:
    """Cập nhật trường hóa đơn (chỉ được phép ở trạng thái DRAFT).
    
    Đối số:
        db: Database session
        invoice_id: ID hóa đơn cần cập nhật
        schema: Các trường cần cập nhật
        org_id: ID tổ chức từ JWT
    
    Trả về:
        Instance ARInvoice được cập nhật
    
    Nâng cao:
        HTTPException: 404 nếu không tìm thấy, 400 nếu đã ghi
    """
    invoice = await get_invoice(db, invoice_id, org_id)
    
    # Chỉ cho phép cập nhật các hóa đơn DRAFT
    if invoice.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update invoice in {invoice.status} status. Only DRAFT invoices can be modified.",
        )
    
    # Nếu customer_id đang được thay đổi, xác thực nó tồn tại
    if schema.customer_id is not None and schema.customer_id != invoice.customer_id:
        customer_query = select(Customer).where(
            Customer.id == schema.customer_id,
            Customer.org_id == org_id,
        )
        customer_result = await db.execute(customer_query)
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer {schema.customer_id} not found in your organization",
            )
    
    # Cập nhật các trường (exclude unset để cho phép cập nhật từng phần)
    update_data = schema.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)
    
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


async def post_invoice(
    db: AsyncSession,
    invoice_id: int,
    org_id: int,
) -> ARInvoice:
    """Ghi hóa đơn (chuyển DRAFT → POSTED).
    
    Sau khi ghi, hóa đơn trở thành bất biến (không thể cập nhật/xóa).
    
    Đối số:
        db: Database session
        invoice_id: ID hóa đơn cần ghi
        org_id: ID tổ chức từ JWT
    
    Trả về:
        Instance ARInvoice được ghi
    
    Nâng cao:
        HTTPException: 404 nếu không tìm thấy, 400 nếu đã ghi hoặc số tiền không hợp lệ
    """
    invoice = await get_invoice(db, invoice_id, org_id)
    
    # Xác thực trạng thái hiện tại
    if invoice.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice is already {invoice.status}. Only DRAFT invoices can be posted.",
        )
    
    # Xác thực total_amount là dương
    if invoice.total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot post invoice with zero or negative total amount",
        )
    
    # Chuyển đổi sang POSTED
    invoice.status = "posted"
    
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


async def delete_invoice(
    db: AsyncSession,
    invoice_id: int,
    org_id: int,
) -> None:
    """Xóa hóa đơn (chỉ được phép ở trạng thái DRAFT).
    
    Đối số:
        db: Database session
        invoice_id: ID hóa đơn cần xóa
        org_id: ID tổ chức từ JWT
    
    Nâng cao:
        HTTPException: 404 nếu không tìm thấy, 400 nếu đã ghi
    """
    invoice = await get_invoice(db, invoice_id, org_id)
    
    # Chỉ cho phép xóa các hóa đơn DRAFT
    if invoice.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete invoice in {invoice.status} status. Only DRAFT invoices can be deleted.",
        )
    
    await db.delete(invoice)
    await db.commit()


async def bulk_import_invoices(
    db: AsyncSession,
    invoices_data: list,
    org_id: int,
    auto_post: bool = False,
) -> dict:
    """Bulk import nhiều hóa đơn từ Excel/CSV.
    
    Đối số:
        db: Database session
        invoices_data: Danh sách các dicts dữ liệu hóa đơn
        org_id: ID tổ chức từ JWT
        auto_post: Nếu True, tự động ghi hóa đơn sau khi tạo
    
    Trả về:
        dict với kết quả import: total_submitted, total_success, total_failed, results
    """
    results = []
    success_count = 0
    failed_count = 0
    
    for inv_data in invoices_data:
        try:
            # Kiểm tra hóa đơn trùng lặp
            existing_query = select(ARInvoice).where(
                ARInvoice.org_id == org_id,
                ARInvoice.invoice_no == inv_data.invoice_no,
            )
            existing_result = await db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                results.append({
                    "invoice_no": inv_data.invoice_no,
                    "success": False,
                    "id": None,
                    "error": f"Invoice number {inv_data.invoice_no} already exists"
                })
                failed_count += 1
                continue
            
            # Tạo hóa đơn
            invoice = ARInvoice(
                org_id=org_id,
                invoice_no=inv_data.invoice_no,
                customer_id=inv_data.customer_id,
                issue_date=inv_data.issue_date,
                due_date=inv_data.due_date,
                total_amount=inv_data.total_amount,
                notes=inv_data.notes,
                status="draft",
                paid_amount=0,
            )
            db.add(invoice)
            await db.flush()  # Lấy ID ngay lập tức
            
            # Tự động ghi nếu được yêu cầu
            if auto_post:
                invoice.status = "posted"
            
            results.append({
                "invoice_no": inv_data.invoice_no,
                "success": True,
                "id": invoice.id,
                "error": None
            })
            success_count += 1
            
        except Exception as e:
            results.append({
                "invoice_no": inv_data.invoice_no,
                "success": False,
                "id": None,
                "error": str(e)
            })
            failed_count += 1
    
    # Commit tất cả các imports thành công
    if success_count > 0:
        await db.commit()
    
    return {
        "total_submitted": len(invoices_data),
        "total_success": success_count,
        "total_failed": failed_count,
        "results": results
    }
