"""Analytics Service - Business logic orchestrator."""

import logging
import trino
import os
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.modules.analytics.services import (
    calculate_dso,
    calculate_dpo,
    calculate_ccc,
    get_ar_aging_buckets,
    get_ap_aging_buckets,
    get_daily_revenue,
    get_payment_success_rate,
    get_reconciliation_status,
    create_export_job,
    get_job_status,
)
from app.modules.analytics.schemas import (
    DashboardSummary,
    ARAgingResponse,
    APAgingResponse,
    DailyRevenueResponse,
    DailyRevenueDataPoint,
    PaymentSuccessRateResponse,
    ReconciliationResponse,
    ReconciliationAutoMatchResponse,
    ReconciliationMatch,
    ReconciliationActionResponse,
)
from app.models.core import Account

logger = logging.getLogger(__name__)


async def get_dashboard_summary(db: AsyncSession, org_id: int) -> DashboardSummary:
    """
    Get complete dashboard summary combining KPI and aging data.
    """
    try:
        # Calculate KPI
        dso = await calculate_dso(db, org_id)
        dpo = await calculate_dpo(db, org_id)
        ccc = await calculate_ccc(dso, dpo)
        
        # Get AR aging data
        total_ar, _, ar_buckets = await get_ar_aging_buckets(db, org_id)
        
        # Get AP aging data
        total_ap, _, ap_buckets = await get_ap_aging_buckets(db, org_id)
        
        # Get cash balance
        cash_balance = await _get_cash_balance(db, org_id)
        
        # Calculate working capital
        working_capital = cash_balance + total_ar - total_ap
        
        # Count overdue invoices
        overdue_ar_count = sum(bucket.count for bucket in ar_buckets if bucket.bucket_days in ["61-90", ">90"])
        overdue_ar_amount = sum(bucket.total_amount for bucket in ar_buckets if bucket.bucket_days in ["61-90", ">90"])
        
        # Count overdue bills
        overdue_ap_count = sum(bucket.count for bucket in ap_buckets if bucket.bucket_days in ["61-90", ">90"])
        overdue_ap_amount = sum(bucket.total_amount for bucket in ap_buckets if bucket.bucket_days in ["61-90", ">90"])
        
        return DashboardSummary(
            dso=dso,
            dpo=dpo,
            ccc=ccc,
            total_ar=total_ar,
            total_ap=total_ap,
            cash_balance=cash_balance,
            working_capital=working_capital,
            overdue_ar_count=overdue_ar_count,
            overdue_ar_amount=overdue_ar_amount,
            overdue_ap_count=overdue_ap_count,
            overdue_ap_amount=overdue_ap_amount,
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise


async def get_ar_aging(db: AsyncSession, org_id: int) -> ARAgingResponse:
    """Get AR aging report."""
    try:
        total_ar, total_invoices, buckets = await get_ar_aging_buckets(db, org_id)
        return ARAgingResponse(
            total_ar=total_ar,
            total_invoices=total_invoices,
            buckets=buckets,
        )
    except Exception as e:
        logger.error(f"Error getting AR aging: {e}")
        raise


async def get_ap_aging(db: AsyncSession, org_id: int) -> APAgingResponse:
    """Get AP aging report."""
    try:
        total_ap, total_bills, buckets = await get_ap_aging_buckets(db, org_id)
        return APAgingResponse(
            total_ap=total_ap,
            total_bills=total_bills,
            buckets=buckets,
        )
    except Exception as e:
        logger.error(f"Error getting AP aging: {e}")
        raise


async def get_daily_revenue_kpi(db: AsyncSession, org_id: int, days: int = 7) -> DailyRevenueResponse:
    """Get daily revenue KPI."""
    try:
        total_revenue, average_daily, daily_data = await get_daily_revenue(db, org_id, days)
        
        # Convert daily_data to DailyRevenueDataPoint objects
        data_points = [
            DailyRevenueDataPoint(date=item["date"], revenue=item["revenue"])
            for item in daily_data
        ]
        
        return DailyRevenueResponse(
            total_revenue=total_revenue,
            average_daily_revenue=average_daily,
            data=data_points,
        )
    except Exception as e:
        logger.error(f"Error getting daily revenue: {e}")
        raise


async def get_payment_success_rate_kpi(db: AsyncSession, org_id: int, days: int = 7) -> PaymentSuccessRateResponse:
    """Get payment success rate KPI."""
    try:
        success_rate, total_transactions, successful, failed = await get_payment_success_rate(db, org_id, days)
        
        return PaymentSuccessRateResponse(
            success_rate=success_rate,
            total_transactions=total_transactions,
            successful=successful,
            failed=failed,
        )
    except Exception as e:
        logger.error(f"Error getting payment success rate: {e}")
        raise


async def get_reconciliation_kpi(db: AsyncSession, org_id: int, reconcile_date: date) -> ReconciliationResponse:
    """Get payment reconciliation status."""
    try:
        total_txns, reconciled, pending, rate, discrepancies = await get_reconciliation_status(
            db, org_id, reconcile_date
        )
        
        return ReconciliationResponse(
            total_transactions=total_txns,
            reconciled=reconciled,
            pending=pending,
            reconciliation_rate=rate,
            discrepancies=discrepancies,
        )
    except Exception as e:
        logger.error(f"Error getting reconciliation status: {e}")
        raise


async def create_export_job_service(
    db: AsyncSession,
    org_id: int,
    report_type: str,
    format: str = "xlsx",
    date_from: str = None,
    date_to: str = None,
) -> str:
    """Create export job."""
    try:
        job_id = await create_export_job(
            db=db,
            org_id=org_id,
            report_type=report_type,
            format=format,
            date_from=date_from,
            date_to=date_to,
        )
        return job_id
    except Exception as e:
        logger.error(f"Error creating export job: {e}")
        raise


async def get_export_job_status(db: AsyncSession, job_id: str, org_id: int) -> dict:
    """Get export job status."""
    try:
        return await get_job_status(db, job_id, org_id)
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise


async def _get_cash_balance(db: AsyncSession, org_id: int) -> Decimal:
    """Get current cash balance from accounts."""
    try:
        from sqlalchemy import select, func
        
        # Note: Account model stores balance in balance column
        # For now return 0 as placeholder - in real system would query account balances
        # This requires Account model to have proper balance tracking
        return Decimal(0)
    except Exception as e:
        logger.error(f"Error getting cash balance: {e}")
        return Decimal(0)


# ============================================================
# ML FORECAST & ANOMALY SERVICES
# ============================================================

def _get_trino_connection():
    """
    Create Trino connection for querying ML Gold tables with timeout.
    
    Returns:
        Trino connection object
    """
    TRINO_TIMEOUT = int(os.getenv("TRINO_TIMEOUT", "40"))  # 40 sec timeout
    conn = trino.dbapi.connect(
        host=os.getenv("TRINO_HOST", "trino"),
        port=int(os.getenv("TRINO_PORT", 8080)),
        user="api_backend",
        catalog="sme_lake",
        schema="gold",
        request_timeout=TRINO_TIMEOUT,  # 40 sec to allow Trino queries to complete
    )
    return conn


async def get_revenue_forecast(
    db: AsyncSession,
    org_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Get revenue forecast predictions from ML model.
    
    Queries sme_lake.gold.ml_cashflow_forecast table via Trino.
    Falls back to PostgreSQL-based estimates if Trino unavailable.
    
    Args:
        db: Database session (used for fallback queries)
        org_id: Organization ID (for future multi-tenancy support)
        start_date: Filter forecasts from this date (optional)
        end_date: Filter forecasts until this date (optional)
    
    Returns:
        List of forecast data points with date, forecast, bounds
    
    Raises:
        Exception: If all queries fail
    """
    try:
        logger.info(f"Fetching revenue forecast for org_id={org_id}, dates={start_date} to {end_date}")
        
        conn = _get_trino_connection()
        cursor = conn.cursor()
        
        # Build query with date filters (Trino doesn't support parameterized queries well)
        query = """
        SELECT 
            forecast_date,
            predicted_cashflow,
            lower_bound,
            upper_bound,
            model_name,
            prediction_timestamp
        FROM sme_lake.gold.ml_cashflow_forecast
        WHERE 1=1
        """
        
        if start_date:
            query += f" AND forecast_date >= DATE '{start_date.isoformat()}'"
        if end_date:
            query += f" AND forecast_date <= DATE '{end_date.isoformat()}'"
        
        query += " ORDER BY forecast_date ASC"
        
        logger.debug(f"Executing Trino query: {query}")
        cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                "actual": None,  # Historical actual data not stored in forecast table
                "forecast": float(row[1]),
                "lower_bound": float(row[2]),
                "upper_bound": float(row[3]),
            })
        
        # If no results with date filter, fetch ALL available data (demo/seed data fallback)
        if len(results) == 0 and (start_date or end_date):
            logger.info("No forecast data in requested date range, fetching all available data")
            all_data_query = """
            SELECT 
                forecast_date,
                predicted_cashflow,
                lower_bound,
                upper_bound,
                model_name,
                prediction_timestamp
            FROM sme_lake.gold.ml_cashflow_forecast
            ORDER BY forecast_date ASC
            """
            cursor.execute(all_data_query)
            for row in cursor.fetchall():
                results.append({
                    "date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    "actual": None,
                    "forecast": float(row[1]),
                    "lower_bound": float(row[2]),
                    "upper_bound": float(row[3]),
                })
            logger.info(f"Fetched {len(results)} forecast points (all available data)")
        
        cursor.close()
        conn.close()
        
        logger.info(f"Retrieved {len(results)} forecast data points from Trino")
        return results
        
    except Exception as e:
        logger.warning(f"Trino unavailable for forecast, using PostgreSQL fallback: {e}")
        
        # Fallback: Generate forecast based on historical payment averages
        try:
            from datetime import timedelta
            import random
            
            # Query historical payments average from PostgreSQL
            pg_query = text("""
                SELECT 
                    AVG(p.amount) as avg_amount,
                    STDDEV(p.amount) as stddev_amount
                FROM finance.payments p
                WHERE p.org_id = :org_id
                AND p.transaction_date >= CURRENT_DATE - INTERVAL '90 days'
            """)
            
            result = await db.execute(pg_query, {"org_id": org_id})
            row = result.fetchone()
            
            avg_amount = float(row[0]) if row and row[0] else 50000000  # Default 50M
            stddev_amount = float(row[1]) if row and row[1] else avg_amount * 0.2
            
            # Generate forecast for requested date range
            results = []
            if not start_date:
                start_date = date.today()
            if not end_date:
                end_date = start_date + timedelta(days=30)
            
            current_date = start_date
            while current_date <= end_date:
                # Simple forecast with some randomization
                base_forecast = avg_amount * (1 + random.uniform(-0.1, 0.1))
                results.append({
                    "date": current_date.isoformat(),
                    "actual": None,
                    "forecast": round(base_forecast, 2),
                    "lower_bound": round(base_forecast - stddev_amount, 2),
                    "upper_bound": round(base_forecast + stddev_amount, 2),
                })
                current_date += timedelta(days=1)
            
            logger.info(f"Generated {len(results)} forecast points from PostgreSQL fallback")
            return results
            
        except Exception as fallback_error:
            logger.error(f"PostgreSQL fallback also failed: {fallback_error}")
            raise


async def get_revenue_anomalies(
    db: AsyncSession,
    org_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    severity: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get revenue anomaly alerts from ML model.
    
    Queries sme_lake.gold.ml_anomaly_alerts table via Trino.
    
    Args:
        db: Database session (not used for Trino queries but kept for consistency)
        org_id: Organization ID (for future multi-tenancy support)
        start_date: Filter anomalies from this date (optional)
        end_date: Filter anomalies until this date (optional)
        severity: Filter by severity level: CRITICAL, HIGH, MEDIUM, LOW (optional)
    
    Returns:
        List of anomaly alerts with date, amount, score, severity
    
    Raises:
        Exception: If Trino query fails
    """
    try:
        logger.info(f"Fetching revenue anomalies for org_id={org_id}, dates={start_date} to {end_date}, severity={severity}")
        
        conn = _get_trino_connection()
        cursor = conn.cursor()
        
        # Build query with filters (Trino string interpolation for dates)
        query = """
        SELECT 
            txn_date,
            amount_vnd,
            anomaly_score,
            severity,
            transaction_category,
            counterparty_name
        FROM sme_lake.gold.ml_anomaly_alerts
        WHERE 1=1
        """
        
        if start_date:
            query += f" AND txn_date >= DATE '{start_date.isoformat()}'"
        if end_date:
            query += f" AND txn_date <= DATE '{end_date.isoformat()}'"
        if severity:
            query += f" AND severity = '{severity.upper()}'"
        
        query += " ORDER BY txn_date DESC, anomaly_score ASC LIMIT 1000"
        
        logger.debug(f"Executing Trino query: {query}")
        cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                "amount": float(row[1]),
                "expected": None,  # Not stored in current schema
                "deviation": float(row[2]),  # anomaly_score
                "severity": row[3],
                "category": row[4] if len(row) > 4 else None,
                "counterparty": row[5] if len(row) > 5 else None,
            })
        
        # If no results with date filter, fetch ALL available data (demo/seed data fallback)
        if len(results) == 0 and (start_date or end_date):
            logger.info("No anomaly data in requested date range, fetching all available data")
            all_data_query = """
            SELECT 
                txn_date,
                amount_vnd,
                anomaly_score,
                severity,
                transaction_category,
                counterparty_name
            FROM sme_lake.gold.ml_anomaly_alerts
            """
            if severity:
                all_data_query += f" WHERE severity = '{severity.upper()}'"
            all_data_query += " ORDER BY anomaly_score ASC LIMIT 1000"
            
            cursor.execute(all_data_query)
            for row in cursor.fetchall():
                results.append({
                    "date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    "amount": float(row[1]),
                    "expected": None,
                    "deviation": float(row[2]),
                    "severity": row[3],
                    "category": row[4] if len(row) > 4 else None,
                    "counterparty": row[5] if len(row) > 5 else None,
                })
            logger.info(f"Fetched {len(results)} anomaly alerts (all available data)")
        
        cursor.close()
        conn.close()
        
        logger.info(f"Retrieved {len(results)} anomaly alerts from Trino")
        return results
        
    except Exception as e:
        logger.warning(f"Trino unavailable for anomalies, using PostgreSQL fallback: {e}")
        
        # Fallback: Detect anomalies from PostgreSQL payment data using statistical methods
        try:
            from datetime import timedelta
            
            # Query payments and calculate outliers using z-score method
            pg_query = text("""
                WITH payment_stats AS (
                    SELECT 
                        AVG(amount) as avg_amount,
                        STDDEV(amount) as stddev_amount
                    FROM finance.payments
                    WHERE org_id = :org_id
                    AND transaction_date >= CURRENT_DATE - INTERVAL '90 days'
                ),
                payment_anomalies AS (
                    SELECT 
                        p.id,
                        p.transaction_date,
                        p.amount,
                        p.reference_code,
                        p.notes,
                        a.name as account_name,
                        (p.amount - ps.avg_amount) / NULLIF(ps.stddev_amount, 0) as z_score
                    FROM finance.payments p
                    CROSS JOIN payment_stats ps
                    LEFT JOIN core.accounts a ON p.account_id = a.id
                    WHERE p.org_id = :org_id
                    AND p.transaction_date >= :start_date
                    AND p.transaction_date <= :end_date
                    AND ABS((p.amount - ps.avg_amount) / NULLIF(ps.stddev_amount, 0)) > 1.5
                )
                SELECT 
                    transaction_date,
                    amount,
                    z_score,
                    CASE 
                        WHEN ABS(z_score) > 3 THEN 'CRITICAL'
                        WHEN ABS(z_score) > 2.5 THEN 'HIGH'
                        WHEN ABS(z_score) > 2 THEN 'MEDIUM'
                        ELSE 'LOW'
                    END as severity,
                    'Statistical Outlier' as category,
                    account_name
                FROM payment_anomalies
                ORDER BY transaction_date DESC
                LIMIT 100
            """)
            
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            result = await db.execute(pg_query, {
                "org_id": org_id,
                "start_date": start_date,
                "end_date": end_date
            })
            rows = result.fetchall()
            
            results = []
            for row in rows:
                # Filter by severity if specified
                if severity and row[3].upper() != severity.upper():
                    continue
                    
                results.append({
                    "date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    "amount": float(row[1]),
                    "expected": None,
                    "deviation": float(row[2]) if row[2] else 0,  # z-score as deviation
                    "severity": row[3],
                    "category": row[4],
                    "counterparty": row[5],
                })
            
            logger.info(f"Generated {len(results)} anomaly alerts from PostgreSQL fallback")
            return results
            
        except Exception as fallback_error:
            logger.error(f"PostgreSQL fallback also failed: {fallback_error}")
            raise


# ============================================================
# RECONCILIATION ACTION SERVICES
# ============================================================

async def auto_match_reconciliation(
    db: AsyncSession,
    org_id: int,
    reconcile_date: date,
    tolerance: float = 1000.0
) -> ReconciliationAutoMatchResponse:
    """
    Auto-match bank transactions with system payments.
    
    This is a simplified implementation that matches payments
    based on amount within a tolerance window.
    
    If reconcile_date is provided, matches for that date only.
    If no payments found on that date, expands search to last 30 days.
    
    In a production system, you would:
    1. Import bank transactions from a separate table
    2. Match using multiple criteria (amount, date, reference)
    3. Use ML for fuzzy matching
    """
    from app.models.finance import Payment
    from sqlalchemy import select
    from datetime import timedelta
    
    try:
        # First try: Get payments for the specific date
        query = select(Payment).where(
            Payment.org_id == org_id,
            Payment.transaction_date == reconcile_date
        )
        result = await db.execute(query)
        payments = result.scalars().all()
        
        # If no payments found on specific date, search last 30 days
        if len(payments) == 0:
            logger.info(f"No payments found for {reconcile_date}, searching last 30 days...")
            start_date = reconcile_date - timedelta(days=30)
            query = select(Payment).where(
                Payment.org_id == org_id,
                Payment.transaction_date >= start_date,
                Payment.transaction_date <= reconcile_date
            ).order_by(Payment.transaction_date.desc()).limit(100)
            result = await db.execute(query)
            payments = result.scalars().all()
            logger.info(f"Found {len(payments)} payments in last 30 days")
        
        # In a real system, we'd have a BankTransaction table
        # For now, we simulate with matching all payments as "matched"
        matches = []
        unmatched_payment_ids = []
        
        for idx, payment in enumerate(payments):
            # Simulate: every payment gets matched to a "bank transaction"
            # with simulated bank_transaction_id = payment.id + 10000
            match = ReconciliationMatch(
                bank_transaction_id=payment.id + 10000,  # Simulated bank ID
                payment_id=payment.id,
                bank_amount=float(payment.amount),
                payment_amount=float(payment.amount),
                match_confidence=100.0,  # Perfect match
                status="matched"
            )
            matches.append(match)
        
        total_bank = len(payments)  # Simulated
        total_matched = len(matches)
        total_unmatched = 0
        
        logger.info(f"Auto-match complete: {total_matched} matches found for org_id={org_id}")
        
        return ReconciliationAutoMatchResponse(
            total_bank_transactions=total_bank,
            total_matched=total_matched,
            total_unmatched=total_unmatched,
            matches=matches,
            unmatched_bank_ids=[],
            unmatched_payment_ids=unmatched_payment_ids,
        )
        
    except Exception as e:
        logger.error(f"Error in auto-match reconciliation: {e}")
        raise


async def confirm_reconciliation(
    db: AsyncSession,
    org_id: int,
    transaction_id: int,
    payment_id: int,
    notes: Optional[str] = None
) -> ReconciliationActionResponse:
    """
    Confirm a reconciliation match.
    
    In production, this would:
    1. Update BankTransaction.status = 'matched'
    2. Link BankTransaction to Payment
    3. Create audit log entry
    """
    try:
        # In a real system, update the bank transaction record
        # For now, we just return success
        
        logger.info(f"Confirmed match: bank_txn={transaction_id}, payment={payment_id}, notes={notes}")
        
        return ReconciliationActionResponse(
            success=True,
            message=f"Successfully matched bank transaction {transaction_id} with payment {payment_id}",
            transaction_id=transaction_id,
            new_status="matched"
        )
        
    except Exception as e:
        logger.error(f"Error confirming reconciliation: {e}")
        raise


async def reject_reconciliation(
    db: AsyncSession,
    org_id: int,
    transaction_id: int
) -> ReconciliationActionResponse:
    """
    Reject a suggested reconciliation match.
    
    In production, this would:
    1. Update BankTransaction.status = 'rejected'
    2. Remove suggested match
    3. Keep transaction in pending list for manual review
    """
    try:
        logger.info(f"Rejected match for bank_txn={transaction_id}")
        
        return ReconciliationActionResponse(
            success=True,
            message=f"Rejected match for bank transaction {transaction_id}",
            transaction_id=transaction_id,
            new_status="rejected"
        )
        
    except Exception as e:
        logger.error(f"Error rejecting reconciliation: {e}")
        raise


async def get_pending_reconciliations(
    db: AsyncSession,
    org_id: int,
    reconcile_date: date
) -> list:
    """
    Get list of pending (unmatched) transactions.
    
    In production, this would query BankTransaction table
    where status = 'pending'.
    """
    from app.models.finance import Payment
    from sqlalchemy import select
    
    try:
        # Get payments that might need reconciliation
        query = select(Payment).where(
            Payment.org_id == org_id,
            Payment.transaction_date == reconcile_date
        )
        result = await db.execute(query)
        payments = result.scalars().all()
        
        # In a real system, we'd return unmatched bank transactions
        # For now, return empty list (all matched in simulation)
        pending = []
        
        return pending
        
    except Exception as e:
        logger.error(f"Error getting pending reconciliations: {e}")
        raise
