"""Dịch vụ thanh toán - Logic kinh doanh cho quản lý thanh toán và phân bổ."""

from datetime import date
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import Payment, PaymentAllocation, ARInvoice, APBill
from app.models.core import Account
from app.schema.finance import PaymentCreate, PaymentUpdate
from app.modules.finance.services.invoice_service import get_invoice


async def get_payments(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_id: Optional[int] = None,
    payment_method: Optional[str] = None,
) -> tuple[Sequence[Payment], int]:
    """Lấy danh sách thanh toán với phân trang và lọc.
    
    Đối số:
        db: Database session
        org_id: ID tổ chức từ JWT
        skip: Độ lệch cho phân trang
        limit: Tối đa bản ghi trả về
        date_from: Lọc theo transaction_date >= date_from
        date_to: Lọc theo transaction_date <= date_to
        account_id: Lọc theo ID tài khoản
        payment_method: Lọc theo phương thức thanh toán (cash, transfer, vietqr, card)
    
    Trả về:
        Tuple (danh sách thanh toán, tổng số)
    """
    # Xây dựng điều kiện truy vấn cơ sở
    conditions = [Payment.org_id == org_id]
    
    if date_from:
        conditions.append(Payment.transaction_date >= date_from)
    if date_to:
        conditions.append(Payment.transaction_date <= date_to)
    if account_id:
        conditions.append(Payment.account_id == account_id)
    if payment_method:
        conditions.append(Payment.payment_method == payment_method)
    
    # Xây dựng query với eager loading phân bổ
    query = (
        select(Payment)
        .where(*conditions)
        .options(selectinload(Payment.allocations))
        .offset(skip)
        .limit(limit)
        .order_by(Payment.transaction_date.desc())
    )
    
    count_query = (
        select(func.count())
        .select_from(Payment)
        .where(*conditions)
    )
    
    # Thực thi các truy vấn
    result = await db.execute(query)
    payments = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    return payments, total


async def get_payment(
    db: AsyncSession,
    payment_id: int,
    org_id: int,
) -> Payment:
    """Lấy một thanh toán theo ID với phân bổ.
    
    Đối số:
        db: Database session
        payment_id: ID thanh toán
        org_id: ID tổ chức từ JWT
    
    Trả về:
        Instance Payment với phân bổ được load
    
    Nâng cao:
        HTTPException: 404 nếu không tìm thấy hoặc thuộc org khác
    """
    query = (
        select(Payment)
        .where(Payment.id == payment_id, Payment.org_id == org_id)
        .options(selectinload(Payment.allocations))
    )
    result = await db.execute(query)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found",
        )
    
    return payment


async def create_payment_with_allocations(
    db: AsyncSession,
    schema: PaymentCreate,
    org_id: int,
) -> Payment:
    """Tạo thanh toán với phân bổ cho hóa đơn/hóa đơn (giao dịch ATOMIC).
    
    Hàm này triển khai logic giao dịch ACID:
    1. Xác thực tài khoản tồn tại
    2. Tạo record Payment
    3. Với mỗi phân bổ:
       - Xác thực hóa đơn tồn tại và thuộc org
       - Xác thực allocated_amount không vượt quá số dư còn lại
       - Tạo record PaymentAllocation
       - Cập nhật paid_amount của hóa đơn
       - Cập nhật trạng thái hóa đơn (partial/paid)
    4. Commit tất cả thay đổi một cách atomic (tất cả hoặc không)
    
    Đối số:
        db: Database session
        schema: Dữ liệu tạo Payment với phân bổ
        org_id: ID tổ chức từ JWT
    
    Trả về:
        Instance Payment được tạo với phân bổ được load
    
    Nâng cao:
        HTTPException: 400 nếu xác thực thất bại (tài khoản, hóa đơn, số tiền phân bổ)
    """
    try:
        # Bước 1: Xác thực tài khoản tồn tại và thuộc org
        account_query = select(Account).where(
            Account.id == schema.account_id,
            Account.org_id == org_id,
        )
        account_result = await db.execute(account_query)
        account = account_result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {schema.account_id} not found in your organization",
            )
        
        # Bước 2: Tạo record payment
        payment = Payment(
            **schema.model_dump(exclude={'allocations'}),
            org_id=org_id,
        )
        db.add(payment)
        await db.flush()  # Đảm bảo payment.id được tạo
        
        # Bước 3: Xử lý từng phân bổ ATOMIC
        for alloc_item in schema.allocations:
            # Xử lý phân bổ hóa đơn AR
            if alloc_item.ar_invoice_id is not None:
                # Xác thực hóa đơn tồn tại và thuộc org
                invoice = await get_invoice(db, alloc_item.ar_invoice_id, org_id)
                
                # Xác thực hóa đơn là POSTED (không thể phân bổ cho DRAFT)
                if invoice.status == "draft":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot allocate payment to DRAFT invoice {invoice.invoice_no}. Post it first.",
                    )
                
                # Tính số dư còn lại
                remaining = invoice.total_amount - invoice.paid_amount
                
                if alloc_item.allocated_amount > remaining:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Allocation amount {alloc_item.allocated_amount} exceeds "
                            f"remaining balance {remaining} for invoice {invoice.invoice_no}"
                        ),
                    )
                
                # Tạo bản ghi phân bổ
                allocation = PaymentAllocation(
                    payment_id=payment.id,
                    ar_invoice_id=alloc_item.ar_invoice_id,
                    allocated_amount=alloc_item.allocated_amount,
                    org_id=org_id,
                )
                db.add(allocation)
                
                # Cập nhật paid_amount của hóa đơn
                invoice.paid_amount += alloc_item.allocated_amount
                
                # Cập nhật trạng thái hóa đơn dựa trên số tiền thanh toán
                if invoice.paid_amount >= invoice.total_amount:
                    invoice.status = "paid"
                else:
                    invoice.status = "partial"
            
            # Xử lý phân bổ hóa đơn AP
            elif alloc_item.ap_bill_id is not None:
                # Truy vấn hóa đơn AP
                bill_query = select(APBill).where(
                    APBill.id == alloc_item.ap_bill_id,
                    APBill.org_id == org_id,
                )
                bill_result = await db.execute(bill_query)
                bill = bill_result.scalar_one_or_none()
                
                if not bill:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"AP Bill {alloc_item.ap_bill_id} not found in your organization",
                    )
                
                # Xác thực hóa đơn là POSTED
                if bill.status == "draft":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot allocate payment to DRAFT bill {bill.bill_no}. Post it first.",
                    )
                
                # Tính số dư còn lại
                remaining = bill.total_amount - bill.paid_amount
                
                if alloc_item.allocated_amount > remaining:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Allocation amount {alloc_item.allocated_amount} exceeds "
                            f"remaining balance {remaining} for bill {bill.bill_no}"
                        ),
                    )
                
                # Tạo bản ghi phân bổ
                allocation = PaymentAllocation(
                    payment_id=payment.id,
                    ap_bill_id=alloc_item.ap_bill_id,
                    allocated_amount=alloc_item.allocated_amount,
                    org_id=org_id,
                )
                db.add(allocation)
                
                # Cập nhật paid_amount của hóa đơn
                bill.paid_amount += alloc_item.allocated_amount
                
                # Cập nhật trạng thái hóa đơn
                if bill.paid_amount >= bill.total_amount:
                    bill.status = "paid"
                else:
                    bill.status = "partial"
        
        # Bước 4: Commit tất cả thay đổi một cách atomic
        await db.commit()
        await db.refresh(payment)
        
        # Tải lại phân bổ
        await db.refresh(payment, attribute_names=['allocations'])
        
        return payment
    
    except HTTPException:
        # Tái tung các ngoại lệ HTTP (lỗi xác thực)
        await db.rollback()
        raise
    except Exception as e:
        # Rollback nếu có lỗi khác
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}",
        )


async def update_payment(
    db: AsyncSession,
    payment_id: int,
    org_id: int,
    schema: PaymentUpdate,
) -> Payment:
    """Cập nhật metadata thanh toán (notes, reference_code chỉ).
    
    CÁC TRƯỜNG BẤT BIẾN - Không thể cập nhật sau khi tạo:
    - amount (tuân thủ audit)
    - transaction_date
    - account_id
    - allocations (phải hủy phân bổ/tái phân bổ nếu cần)
    
    Quy tắc kinh doanh:
    - Chỉ có thể sửa đổi notes và reference_code
    - Tất cả các trường khác bị khóa audit (bất biến)
    - Hữu ích để thêm chi tiết giao dịch ngân hàng sau khi tạo
    
    Đối số:
        db: Database session
        payment_id: ID thanh toán cần cập nhật
        org_id: ID tổ chức từ JWT
        schema: Cập nhật dữ liệu (notes, reference_code)
    
    Trả về:
        Instance Payment được cập nhật với phân bổ được load
    
    Nâng cao:
        404: Nếu thanh toán không tìm thấy
        400: Nếu cố gắng cập nhật các trường bất biến
    """
    try:
        # Truy vấn thanh toán với phân bổ
        query = (
            select(Payment)
            .where(Payment.id == payment_id, Payment.org_id == org_id)
            .options(selectinload(Payment.allocations))
        )
        result = await db.execute(query)
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment {payment_id} not found in your organization",
            )
        
        # Cập nhật chỉ các trường được phép
        if schema.notes is not None:
            payment.notes = schema.notes
        
        if schema.reference_code is not None:
            payment.reference_code = schema.reference_code
        
        # Commit thay đổi
        await db.commit()
        await db.refresh(payment, attribute_names=['allocations'])
        
        return payment
    
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payment: {str(e)}",
        )

