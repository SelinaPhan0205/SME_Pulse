"""Service Điều hòa - Trạng thái điều hòa thanh toán."""

import logging
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance import Payment
from datetime import datetime, date

logger = logging.getLogger(__name__)


async def get_reconciliation_status(
    db: AsyncSession, 
    org_id: int, 
    reconcile_date: date
) -> tuple[int, int, int, float, list]:
    """
    Lấy trạng thái điều hòa thanh toán cho một ngày cụ thể.
    Trả lại: (tổng_giao_dịch, số_đã_điều_hòa, số_chờ_xử_lý, tỷ_lệ_điều_hòa%, danh_sách_chênh_lệch)
    
    Ghi chú: Đây là một triển khai đơn giản hóa. Trong một hệ thống thực, bạn sẽ:
    1. So sánh giao dịch ngân hàng với các khoản thanh toán được ghi lại
    2. Theo dõi reconciliation_status trong bảng Payment
    3. Xác định và lưu trữ các chênh lệch
    """
    try:
        # Đếm tổng số khoản thanh toán cho ngày hôm đó
        total_query = select(func.count(Payment.id)).where(
            Payment.org_id == org_id,
            Payment.transaction_date == reconcile_date
        )
        total_result = await db.execute(total_query)
        total_transactions = total_result.scalar() or 0
        
        if total_transactions == 0:
            return 0, 0, 0, 0.0, []
        
        # Hiện tại, giả sử tất cả các khoản thanh toán đều được điều hòa (không có chênh lệch)
        # Trong một hệ thống thực, bạn sẽ theo dõi reconciliation_status và số dư ngân hàng thực tế
        reconciled_count = total_transactions
        pending_count = 0
        reconciliation_rate = 100.0
        discrepancies = []
        
        logger.info(f"Reconciliation status for org_id={org_id}, date={reconcile_date}: {reconciliation_rate:.2f}%")
        return total_transactions, reconciled_count, pending_count, reconciliation_rate, discrepancies
        
    except Exception as e:
        logger.error(f"Error calculating reconciliation status: {e}")
        return 0, 0, 0, 0.0, []
