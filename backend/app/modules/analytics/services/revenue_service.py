"""Revenue Service - Daily revenue KPI."""

import logging
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance import ARInvoice
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def get_daily_revenue(db: AsyncSession, org_id: int, days: int = 7) -> tuple[Decimal, Decimal, list]:
    """
    Get daily revenue for last N days.
    Returns: (total_revenue, average_daily_revenue, daily_data_list)
    """
    try:
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=days - 1)
        
        # Get all invoices in date range
        query = select(
            ARInvoice.issue_date,
            func.sum(ARInvoice.total_amount)
        ).where(
            ARInvoice.org_id == org_id,
            ARInvoice.issue_date >= start_date,
            ARInvoice.issue_date <= today,
            ARInvoice.status.in_(["posted", "partial", "paid", "overdue"])
        ).group_by(
            ARInvoice.issue_date
        ).order_by(
            ARInvoice.issue_date
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        # Calculate totals
        total_revenue = sum(amount for _, amount in rows) if rows else Decimal(0)
        average_daily_revenue = (total_revenue / days) if days > 0 else Decimal(0)
        
        # Format daily data
        daily_data = []
        for date, amount in rows:
            daily_data.append({
                "date": str(date),
                "revenue": amount or Decimal(0)
            })
        
        logger.info(f"Calculated daily revenue for org_id={org_id}: total={total_revenue}, avg={average_daily_revenue}")
        return total_revenue, average_daily_revenue, daily_data
        
    except Exception as e:
        logger.error(f"Error calculating daily revenue: {e}")
        return Decimal(0), Decimal(0), []
