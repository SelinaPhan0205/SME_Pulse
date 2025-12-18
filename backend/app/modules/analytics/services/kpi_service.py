"""KPI Service - Calculate DSO, DPO, CCC."""

import logging
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance import ARInvoice, APBill
from app.models.core import Account
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def calculate_dso(db: AsyncSession, org_id: int) -> float:
    """
    Calculate Days Sales Outstanding (DSO).
    Formula: (Total AR / Daily Revenue) * 30
    
    Approximation: (Total AR / Total Invoice Amount Last 30 Days) * 30
    """
    try:
        # Get total AR
        ar_query = select(func.sum(ARInvoice.total_amount - ARInvoice.paid_amount)).where(
            ARInvoice.org_id == org_id,
            ARInvoice.status.in_(["posted", "partial", "overdue"])
        )
        ar_result = await db.execute(ar_query)
        total_ar = ar_result.scalar() or Decimal(0)
        
        # Get invoices from last 30 days
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        revenue_query = select(func.sum(ARInvoice.total_amount)).where(
            ARInvoice.org_id == org_id,
            ARInvoice.issue_date >= thirty_days_ago
        )
        revenue_result = await db.execute(revenue_query)
        revenue_30d = revenue_result.scalar() or Decimal(0)
        
        if revenue_30d == 0:
            return 0.0
        
        dso = float((total_ar / revenue_30d) * 30)
        logger.info(f"Calculated DSO={dso:.2f} for org_id={org_id}")
        return dso
        
    except Exception as e:
        logger.error(f"Error calculating DSO: {e}")
        return 0.0


async def calculate_dpo(db: AsyncSession, org_id: int) -> float:
    """
    Calculate Days Payable Outstanding (DPO).
    Formula: (Total AP / Daily Cost of Goods Sold) * 30
    
    Approximation: (Total AP / Total Bill Amount Last 30 Days) * 30
    """
    try:
        # Get total AP
        ap_query = select(func.sum(APBill.total_amount - APBill.paid_amount)).where(
            APBill.org_id == org_id,
            APBill.status.in_(["unpaid", "partial"])
        )
        ap_result = await db.execute(ap_query)
        total_ap = ap_result.scalar() or Decimal(0)
        
        # Get bills from last 30 days
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        bill_query = select(func.sum(APBill.total_amount)).where(
            APBill.org_id == org_id,
            APBill.issue_date >= thirty_days_ago
        )
        bill_result = await db.execute(bill_query)
        bills_30d = bill_result.scalar() or Decimal(0)
        
        if bills_30d == 0:
            return 0.0
        
        dpo = float((total_ap / bills_30d) * 30)
        logger.info(f"Calculated DPO={dpo:.2f} for org_id={org_id}")
        return dpo
        
    except Exception as e:
        logger.error(f"Error calculating DPO: {e}")
        return 0.0


async def calculate_ccc(dso: float, dpo: float) -> float:
    """
    Calculate Cash Conversion Cycle (CCC).
    Formula: DSO - DPO
    """
    ccc = dso - dpo
    return ccc
