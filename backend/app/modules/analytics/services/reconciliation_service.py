"""Reconciliation Service - Payment reconciliation status."""

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
    Get payment reconciliation status for a specific date.
    Returns: (total_transactions, reconciled_count, pending_count, reconciliation_rate%, discrepancies_list)
    
    Note: This is a simplified implementation. In a real system, you would:
    1. Compare bank transactions with recorded payments
    2. Track reconciliation_status in Payment table
    3. Identify and store discrepancies
    """
    try:
        # Count total payments for the date
        total_query = select(func.count(Payment.id)).where(
            Payment.org_id == org_id,
            Payment.transaction_date == reconcile_date
        )
        total_result = await db.execute(total_query)
        total_transactions = total_result.scalar() or 0
        
        if total_transactions == 0:
            return 0, 0, 0, 0.0, []
        
        # For now, assume all payments are reconciled (no discrepancies)
        # In a real system, you would track reconciliation_status and actual bank balance
        reconciled_count = total_transactions
        pending_count = 0
        reconciliation_rate = 100.0
        discrepancies = []
        
        logger.info(f"Reconciliation status for org_id={org_id}, date={reconcile_date}: {reconciliation_rate:.2f}%")
        return total_transactions, reconciled_count, pending_count, reconciliation_rate, discrepancies
        
    except Exception as e:
        logger.error(f"Error calculating reconciliation status: {e}")
        return 0, 0, 0, 0.0, []
