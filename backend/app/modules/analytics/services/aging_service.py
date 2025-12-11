"""Aging Service - AR/AP aging bucket calculations."""

import logging
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance import ARInvoice, APBill
from datetime import datetime, timedelta
from app.modules.analytics.schemas import AgingBucketDetail

logger = logging.getLogger(__name__)


async def get_ar_aging_buckets(db: AsyncSession, org_id: int) -> tuple[Decimal, int, list[AgingBucketDetail]]:
    """
    Calculate AR aging buckets: 0-30, 31-60, 61-90, >90 days.
    Returns: (total_ar, total_invoices, buckets_list)
    """
    try:
        today = datetime.utcnow().date()
        
        # Get total AR
        total_query = select(func.sum(ARInvoice.total_amount - ARInvoice.paid_amount)).where(
            ARInvoice.org_id == org_id,
            ARInvoice.status.in_(["posted", "partial", "overdue"])
        )
        total_result = await db.execute(total_query)
        total_ar = total_result.scalar() or Decimal(0)
        
        # Get invoice count
        count_query = select(func.count(ARInvoice.id)).where(
            ARInvoice.org_id == org_id,
            ARInvoice.status.in_(["posted", "partial", "overdue"])
        )
        count_result = await db.execute(count_query)
        total_invoices = count_result.scalar() or 0
        
        buckets = []
        
        # 0-30 days
        bucket_30 = await _get_ar_bucket(db, org_id, 0, 30, today, total_ar)
        buckets.append(bucket_30)
        
        # 31-60 days
        bucket_60 = await _get_ar_bucket(db, org_id, 31, 60, today, total_ar)
        buckets.append(bucket_60)
        
        # 61-90 days
        bucket_90 = await _get_ar_bucket(db, org_id, 61, 90, today, total_ar)
        buckets.append(bucket_90)
        
        # >90 days
        bucket_90plus = await _get_ar_bucket(db, org_id, 91, 999, today, total_ar)
        buckets.append(bucket_90plus)
        
        logger.info(f"Calculated AR aging for org_id={org_id}: total={total_ar}, invoices={total_invoices}")
        return total_ar, total_invoices, buckets
        
    except Exception as e:
        logger.error(f"Error calculating AR aging: {e}")
        return Decimal(0), 0, []


async def _get_ar_bucket(
    db: AsyncSession, 
    org_id: int, 
    min_days: int, 
    max_days: int, 
    today,
    total_ar: Decimal
) -> AgingBucketDetail:
    """Get single AR aging bucket."""
    min_date = today - timedelta(days=max_days)
    max_date = today - timedelta(days=min_days)
    
    query = select(
        func.count(ARInvoice.id),
        func.sum(ARInvoice.total_amount - ARInvoice.paid_amount)
    ).where(
        ARInvoice.org_id == org_id,
        ARInvoice.due_date >= min_date,
        ARInvoice.due_date <= max_date,
        ARInvoice.status.in_(["posted", "partial", "overdue"])
    )
    
    result = await db.execute(query)
    count, amount = result.one()
    count = count or 0
    amount = amount or Decimal(0)
    percentage = float((amount / total_ar * 100) if total_ar > 0 else 0)
    
    bucket_label = f"{min_days}-{max_days}" if max_days < 999 else f">{min_days}"
    
    return AgingBucketDetail(
        bucket_days=bucket_label,
        count=count,
        total_amount=amount,
        percentage=percentage
    )


async def get_ap_aging_buckets(db: AsyncSession, org_id: int) -> tuple[Decimal, int, list[AgingBucketDetail]]:
    """
    Calculate AP aging buckets: 0-30, 31-60, 61-90, >90 days.
    Returns: (total_ap, total_bills, buckets_list)
    """
    try:
        today = datetime.utcnow().date()
        
        # Get total AP
        total_query = select(func.sum(APBill.total_amount - APBill.paid_amount)).where(
            APBill.org_id == org_id,
            APBill.status.in_(["unpaid", "partial"])
        )
        total_result = await db.execute(total_query)
        total_ap = total_result.scalar() or Decimal(0)
        
        # Get bill count
        count_query = select(func.count(APBill.id)).where(
            APBill.org_id == org_id,
            APBill.status.in_(["unpaid", "partial"])
        )
        count_result = await db.execute(count_query)
        total_bills = count_result.scalar() or 0
        
        buckets = []
        
        # 0-30 days
        bucket_30 = await _get_ap_bucket(db, org_id, 0, 30, today, total_ap)
        buckets.append(bucket_30)
        
        # 31-60 days
        bucket_60 = await _get_ap_bucket(db, org_id, 31, 60, today, total_ap)
        buckets.append(bucket_60)
        
        # 61-90 days
        bucket_90 = await _get_ap_bucket(db, org_id, 61, 90, today, total_ap)
        buckets.append(bucket_90)
        
        # >90 days
        bucket_90plus = await _get_ap_bucket(db, org_id, 91, 999, today, total_ap)
        buckets.append(bucket_90plus)
        
        logger.info(f"Calculated AP aging for org_id={org_id}: total={total_ap}, bills={total_bills}")
        return total_ap, total_bills, buckets
        
    except Exception as e:
        logger.error(f"Error calculating AP aging: {e}")
        return Decimal(0), 0, []


async def _get_ap_bucket(
    db: AsyncSession, 
    org_id: int, 
    min_days: int, 
    max_days: int, 
    today,
    total_ap: Decimal
) -> AgingBucketDetail:
    """Get single AP aging bucket."""
    min_date = today - timedelta(days=max_days)
    max_date = today - timedelta(days=min_days)
    
    query = select(
        func.count(APBill.id),
        func.sum(APBill.total_amount - APBill.paid_amount)
    ).where(
        APBill.org_id == org_id,
        APBill.due_date >= min_date,
        APBill.due_date <= max_date,
        APBill.status.in_(["unpaid", "partial"])
    )
    
    result = await db.execute(query)
    count, amount = result.one()
    count = count or 0
    amount = amount or Decimal(0)
    percentage = float((amount / total_ap * 100) if total_ap > 0 else 0)
    
    bucket_label = f"{min_days}-{max_days}" if max_days < 999 else f">{min_days}"
    
    return AgingBucketDetail(
        bucket_days=bucket_label,
        count=count,
        total_amount=amount,
        percentage=percentage
    )
