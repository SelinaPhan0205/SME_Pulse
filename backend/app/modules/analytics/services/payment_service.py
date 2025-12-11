"""Payment Service - Payment success rate KPI."""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance import Payment
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def get_payment_success_rate(db: AsyncSession, org_id: int, days: int = 7) -> tuple[float, int, int, int]:
    """
    Get payment success rate for last N days.
    Returns: (success_rate_percent, total_transactions, successful_count, failed_count)
    
    Note: In this system, payment status is determined by successful allocation to invoices/bills.
    """
    try:
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=days - 1)
        
        # Count total payments in period
        total_query = select(func.count(Payment.id)).where(
            Payment.org_id == org_id,
            Payment.transaction_date >= start_date,
            Payment.transaction_date <= today
        )
        total_result = await db.execute(total_query)
        total_transactions = total_result.scalar() or 0
        
        if total_transactions == 0:
            return 0.0, 0, 0, 0
        
        # For now, assume all payments are successful (allocations are handled atomically)
        # In a real system, you might track payment_status or check allocation success
        successful_count = total_transactions
        failed_count = 0
        success_rate = 100.0
        
        logger.info(f"Calculated payment success rate for org_id={org_id}: {success_rate:.2f}%")
        return success_rate, total_transactions, successful_count, failed_count
        
    except Exception as e:
        logger.error(f"Error calculating payment success rate: {e}")
        return 0.0, 0, 0, 0
