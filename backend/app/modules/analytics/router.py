"""Analytics Router - Real-time KPI and reporting APIs."""

import logging
import json
import time
import uuid
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from celery.result import AsyncResult

from app.db.session import get_db
from app.models.core import User
from app.modules.auth.dependencies import get_current_user
from app.modules.analytics import service
from app.modules.analytics import tasks
from app.core.config import settings
from app.core.celery_config import celery_app
from app.modules.analytics.schemas import (
    DashboardSummary,
    ARAgingResponse,
    APAgingResponse,
    DailyRevenueResponse,
    PaymentSuccessRateResponse,
    ReconciliationResponse,
    ExportJobResponse,
    MetabaseTokenResponse,
    ForecastResponse,
    AnomalyResponse,
    ReconciliationAutoMatchResponse,
    ReconciliationConfirmRequest,
    ReconciliationActionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# DASHBOARD & KPI ENDPOINTS
# ============================================================

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete dashboard KPI summary.
    
    **UC08 - Dashboard**
    
    Returns:
    - DSO, DPO, CCC, Total AR/AP, Cash Balance, Working Capital
    - Overdue invoice/bill counts and amounts
    - Real-time data from Application DB
    """
    try:
        summary = await service.get_dashboard_summary(db, current_user.org_id)
        logger.info(f"Retrieved dashboard summary for org_id={current_user.org_id}")
        return summary
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard summary"
        )


# ============================================================
# AGING REPORTS
# ============================================================

@router.get("/aging/ar", response_model=ARAgingResponse)
async def get_ar_aging(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get AR (Accounts Receivable) aging report.
    
    **UC05 - Công nợ AR**
    
    Returns:
    - Total AR amount and invoice count
    - Breakdown by aging buckets: 0-30, 31-60, 61-90, >90 days
    - Amount and count for each bucket
    """
    try:
        aging = await service.get_ar_aging(db, current_user.org_id)
        logger.info(f"Retrieved AR aging for org_id={current_user.org_id}")
        return aging
    except Exception as e:
        logger.error(f"Error getting AR aging: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AR aging report"
        )


@router.get("/aging/ap", response_model=APAgingResponse)
async def get_ap_aging(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get AP (Accounts Payable) aging report.
    
    **UC06 - Công nợ AP**
    
    Returns:
    - Total AP amount and bill count
    - Breakdown by aging buckets: 0-30, 31-60, 61-90, >90 days
    - Amount and count for each bucket
    """
    try:
        aging = await service.get_ap_aging(db, current_user.org_id)
        logger.info(f"Retrieved AP aging for org_id={current_user.org_id}")
        return aging
    except Exception as e:
        logger.error(f"Error getting AP aging: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AP aging report"
        )


# ============================================================
# KPI ENDPOINTS
# ============================================================

@router.get("/kpi/daily-revenue", response_model=DailyRevenueResponse)
async def get_daily_revenue(
    days: int = Query(7, ge=1, le=90, description="Number of days to retrieve"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get daily revenue KPI for last N days.
    
    **UC08 - Dashboard (mini chart)**
    
    Query Parameters:
    - days: Number of days (default: 7, max: 90)
    
    Returns:
    - Total revenue, average daily revenue
    - Daily breakdown with date and amount
    """
    try:
        revenue = await service.get_daily_revenue_kpi(db, current_user.org_id, days)
        logger.info(f"Retrieved daily revenue for org_id={current_user.org_id}")
        return revenue
    except Exception as e:
        logger.error(f"Error getting daily revenue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve daily revenue"
        )


@router.get("/kpi/payment-success-rate", response_model=PaymentSuccessRateResponse)
async def get_payment_success_rate(
    days: int = Query(7, ge=1, le=90, description="Number of days to retrieve"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get payment success rate KPI for last N days.
    
    **UC08 - Dashboard (mini chart)**
    **UC05 - Payments (Reconcile tab)**
    
    Query Parameters:
    - days: Number of days (default: 7, max: 90)
    
    Returns:
    - Success rate percentage
    - Total transactions, successful count, failed count
    """
    try:
        success_rate = await service.get_payment_success_rate_kpi(db, current_user.org_id, days)
        logger.info(f"Retrieved payment success rate for org_id={current_user.org_id}")
        return success_rate
    except Exception as e:
        logger.error(f"Error getting payment success rate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment success rate"
        )


@router.get("/kpi/reconciliation", response_model=ReconciliationResponse)
async def get_reconciliation(
    reconcile_date: Optional[date] = Query(None, description="Date to reconcile (default: today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get payment reconciliation status for a specific date.
    
    **UC05 - Payments (Reconcile tab)**
    
    Query Parameters:
    - reconcile_date: Date to reconcile (default: today, format: YYYY-MM-DD)
    
    Returns:
    - Total transactions, reconciled count, pending count
    - Reconciliation rate percentage
    - List of discrepancies
    """
    try:
        if reconcile_date is None:
            reconcile_date = datetime.utcnow().date()
        
        reconciliation = await service.get_reconciliation_kpi(db, current_user.org_id, reconcile_date)
        logger.info(f"Retrieved reconciliation status for org_id={current_user.org_id}, date={reconcile_date}")
        return reconciliation
    except Exception as e:
        logger.error(f"Error getting reconciliation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reconciliation status"
        )


# ============================================================
# RECONCILIATION ACTION ENDPOINTS
# ============================================================

@router.post("/reconciliation/auto-match", response_model=ReconciliationAutoMatchResponse)
async def auto_match_transactions(
    reconcile_date: Optional[date] = Query(None, description="Date to reconcile (default: today)"),
    tolerance: float = Query(1000.0, ge=0, description="Amount tolerance in VND for matching"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Auto-match bank transactions with system payments.
    
    **UC05 - Payment Reconciliation**
    
    Algorithm:
    1. Get all bank transactions for the date
    2. Get all system payments for the date
    3. Match by amount within tolerance (±tolerance VND)
    4. Return matched pairs and unmatched transactions
    
    Query Parameters:
    - reconcile_date: Date to reconcile (default: today)
    - tolerance: Amount tolerance for matching (default: 1000 VND)
    """
    try:
        if reconcile_date is None:
            reconcile_date = datetime.utcnow().date()
        
        result = await service.auto_match_reconciliation(
            db=db,
            org_id=current_user.org_id,
            reconcile_date=reconcile_date,
            tolerance=tolerance
        )
        logger.info(f"Auto-match reconciliation for org_id={current_user.org_id}, date={reconcile_date}: {result.total_matched} matched")
        return result
    except Exception as e:
        logger.error(f"Error in auto-match reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to auto-match transactions"
        )


@router.post("/reconciliation/{transaction_id}/confirm", response_model=ReconciliationActionResponse)
async def confirm_reconciliation_match(
    transaction_id: int,
    request: ReconciliationConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Confirm a reconciliation match between bank transaction and payment.
    
    **UC05 - Manual Reconciliation Confirmation**
    
    Path Parameters:
    - transaction_id: Bank transaction ID to confirm
    
    Request Body:
    - bank_transaction_id: Bank transaction ID
    - payment_id: System payment ID to match
    - notes: Optional notes for audit trail
    """
    try:
        result = await service.confirm_reconciliation(
            db=db,
            org_id=current_user.org_id,
            transaction_id=transaction_id,
            payment_id=request.payment_id,
            notes=request.notes
        )
        logger.info(f"Confirmed reconciliation for transaction_id={transaction_id}, payment_id={request.payment_id}")
        return result
    except Exception as e:
        logger.error(f"Error confirming reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm reconciliation"
        )


@router.post("/reconciliation/{transaction_id}/reject", response_model=ReconciliationActionResponse)
async def reject_reconciliation_match(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reject a suggested reconciliation match.
    
    **UC05 - Reject Reconciliation**
    
    Path Parameters:
    - transaction_id: Bank transaction ID to reject suggested match
    """
    try:
        result = await service.reject_reconciliation(
            db=db,
            org_id=current_user.org_id,
            transaction_id=transaction_id
        )
        logger.info(f"Rejected reconciliation for transaction_id={transaction_id}")
        return result
    except Exception as e:
        logger.error(f"Error rejecting reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject reconciliation"
        )


@router.get("/reconciliation/pending")
async def get_pending_reconciliations(
    reconcile_date: Optional[date] = Query(None, description="Date to check (default: today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of unmatched/pending transactions for reconciliation.
    
    **UC05 - View Pending Reconciliation**
    
    Returns transactions that have not been matched yet.
    """
    try:
        if reconcile_date is None:
            reconcile_date = datetime.utcnow().date()
        
        pending = await service.get_pending_reconciliations(
            db=db,
            org_id=current_user.org_id,
            reconcile_date=reconcile_date
        )
        return {
            "date": reconcile_date.isoformat(),
            "pending_count": len(pending),
            "transactions": pending
        }
    except Exception as e:
        logger.error(f"Error getting pending reconciliations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending reconciliations"
        )


# ============================================================
# EXPORT ENDPOINTS
# ============================================================

@router.post("/reports/export", response_model=ExportJobResponse, status_code=202)
async def export_report(
    report_type: str = Query(..., description="ar_aging, ap_aging, cashflow"),
    format: str = Query("xlsx", description="xlsx only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create async export job for report generation.
    
    **STEP 4 - Excel Export Worker**
    
    Query Parameters:
    - report_type: ar_aging, ap_aging, or cashflow
    - format: xlsx (default)
    
    Returns:
    - job_id: Use to poll status via GET /reports/jobs/{job_id}
    - status: pending (processing in background)
    
    Notes:
    - Export is processed asynchronously (5-30 seconds)
    - Poll job status to get download URL
    - Download URL expires after 48 hours
    """
    try:
        # Validate report_type
        valid_types = ["ar_aging", "ap_aging", "cashflow"]
        if report_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report_type. Must be one of: {valid_types}"
            )
        
        # Validate format
        if format != "xlsx":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only xlsx format is supported"
            )
        
        # Route to correct Celery task (get task_id from Celery)
        if report_type == "ar_aging":
            celery_task = tasks.export_ar_aging.delay(current_user.org_id)
        elif report_type == "ap_aging":
            celery_task = tasks.export_ap_aging.delay(current_user.org_id)
        elif report_type == "cashflow":
            celery_task = tasks.export_cashflow_forecast.delay(current_user.org_id)
        
        # Use Celery task ID as job_id
        job_id = celery_task.id
        
        logger.info(f"Created export job {job_id} for org_id={current_user.org_id}, type={report_type}")
        
        return ExportJobResponse(
            job_id=job_id,
            status="pending",
            report_type=report_type,
            format=format,
            file_url=None,
            error_message=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating export job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export job"
        )


@router.get("/reports/jobs/{job_id}", response_model=ExportJobResponse)
async def get_export_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Poll export job status and get download URL.
    
    **STEP 4 - Excel Export Worker**
    
    Path Parameters:
    - job_id: Job ID from POST /reports/export
    
    Returns:
    - status: pending → processing → completed (or failed)
    - file_url: Download link (48h expiry)
    - progress: 0-100%
    
    Polling Strategy:
    - Pending: Retry every 2-5 seconds
    - Processing: Retry every 1-2 seconds
    - Completed: Use file_url to download
    - Failed: Check error_message for details
    """
    try:
        # Get Celery task result
        task_result = AsyncResult(job_id, app=celery_app)
        
        # Map Celery states to our states
        if task_result.state == "PENDING":
            status_val = "pending"
            file_url = None
            error_message = None
            
        elif task_result.state == "PROGRESS":
            status_val = "processing"
            file_url = None
            error_message = None
            meta = task_result.info or {}
            
        elif task_result.state == "SUCCESS":
            status_val = "completed"
            result = task_result.result or {}
            file_url = result.get("file_url")
            error_message = None
            
        elif task_result.state == "FAILURE":
            status_val = "failed"
            file_url = None
            error_message = str(task_result.info or "Unknown error")
            
        else:
            status_val = "pending"
            file_url = None
            error_message = None
        
        logger.info(f"Job {job_id} status: {status_val}")
        
        return ExportJobResponse(
            job_id=job_id,
            status=status_val,
            report_type="ar_aging",  # Default, would be tracked if stored in DB
            format="xlsx",
            file_url=file_url,
            error_message=error_message,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )
    try:
        job_status = await service.get_export_job_status(db, job_id, current_user.org_id)
        logger.info(f"Retrieved export job status for job_id={job_id}, org_id={current_user.org_id}")
        return ExportJobResponse(**job_status)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting export job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )


# ============================================================
# METABASE EMBEDDING ENDPOINTS
# ============================================================

@router.get("/metabase-token", response_model=MetabaseTokenResponse)
async def get_metabase_token(
    resource_id: int = Query(..., description="Metabase resource ID (dashboard or question)"),
    resource_type: str = Query("dashboard", description="Resource type: 'dashboard' or 'question'"),
    current_user: User = Depends(get_current_user),
):
    """
    Generate JWT token for Metabase dashboard/question embedding.
    
    **UC03 - Metabase Embedding**
    
    Query Parameters:
    - resource_id: Metabase resource ID (e.g., 2, 5)
    - resource_type: Type of resource - 'dashboard' or 'question' (default: dashboard)
    
    Available Dashboards:
    - resource_id=2 → Cashflow Forecast Dashboard
    - resource_id=5 → Anomaly Alerts Dashboard
    
    Returns:
    - token: JWT token for embedding
    - embed_url: Full URL for iframe src attribute
    - resource_id: The requested resource ID
    - expires_in: Token expiration time in seconds
    
    Usage in Frontend:
    ```javascript
    // Get token for Cashflow Forecast Dashboard
    const response = await fetch('/api/v1/analytics/metabase-token?resource_id=2');
    const data = await response.json();
    
    // Embed in iframe
    <iframe src={data.embed_url} frameBorder="0" width="100%" height="800" />
    ```
    
    Notes:
    - Token is valid for 10 minutes (600 seconds)
    - Each request generates a new token
    - Token is signed with Metabase embedding secret key
    - Works for both dashboards and questions (queries)
    """
    try:
        import hashlib
        import hmac
        import base64
        
        # Validate resource_type
        if resource_type not in ["dashboard", "question"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="resource_type must be 'dashboard' or 'question'"
            )
        
        # Create payload for JWT
        payload = {
            "resource": {resource_type: resource_id},
            "params": {"user_id": current_user.id, "org_id": current_user.org_id},
            "iat": int(time.time()),
            "exp": int(time.time()) + settings.METABASE_TOKEN_EXPIRE_SECONDS,
        }
        
        # Encode JWT using HMAC with secret key
        # Metabase uses HS256 algorithm
        secret = settings.METABASE_EMBEDDING_SECRET_KEY
        
        # Create JWT manually for compatibility with Metabase
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Create signature
        message = f"{header}.{payload_str}"
        signature = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        ).decode().rstrip('=')
        
        token = f"{message}.{signature}"
        
        # Construct embed URL based on resource type
        if resource_type == "question":
            embed_url = f"{settings.METABASE_SITE_URL}/embed/question/{token}#bordered=true&titled=true"
        else:
            embed_url = f"{settings.METABASE_SITE_URL}/embed/dashboard/{token}#bordered=true&titled=true"
        
        logger.info(f"Generated Metabase token for {resource_type}_id={resource_id}, user_id={current_user.id}")
        
        return MetabaseTokenResponse(
            token=token,
            embed_url=embed_url,
            dashboard_id=resource_id,
            expires_in=settings.METABASE_TOKEN_EXPIRE_SECONDS,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating Metabase token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding token"
        )


# ============================================================
# ML FORECAST & ANOMALY ENDPOINTS
# ============================================================

@router.get("/forecast/revenue", response_model=ForecastResponse)
async def get_forecast_revenue(
    start_date: Optional[date] = Query(None, description="Filter forecasts from this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter forecasts until this date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get revenue forecast predictions from Prophet ML model.
    
    **UC09 - Cashflow Forecasting**
    
    Query Parameters:
    - start_date: Filter forecasts from this date (optional)
    - end_date: Filter forecasts until this date (optional)
    
    Returns:
    - List of forecast data points with predicted cashflow, confidence bounds
    - Model metadata (name, prediction timestamp)
    
    Example:
    - GET /api/v1/analytics/forecast/revenue?start_date=2024-12-01&end_date=2024-12-31
    
    Notes:
    - Forecasts are generated daily by Airflow ML pipeline
    - Data source: sme_lake.gold.ml_cashflow_forecast (Trino)
    - Model: Prophet v1 trained on historical cashflow data
    """
    try:
        logger.info(f"Fetching revenue forecast for org_id={current_user.org_id}, dates={start_date} to {end_date}")
        
        # Query forecast data from Trino Gold layer
        forecast_data = await service.get_revenue_forecast(
            db=db,
            org_id=current_user.org_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Calculate severity breakdown
        total_days = len(forecast_data)
        
        return ForecastResponse(
            data=forecast_data,
            model_name="prophet_cashflow_v1",
            total_days=total_days,
            timestamp=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Error fetching revenue forecast: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve revenue forecast: {str(e)}"
        )


@router.get("/anomalies/revenue", response_model=AnomalyResponse)
async def get_revenue_anomalies(
    start_date: Optional[date] = Query(None, description="Filter anomalies from this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter anomalies until this date (YYYY-MM-DD)"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get revenue anomaly detection alerts from Isolation Forest ML model.
    
    **UC10 - Anomaly Detection**
    
    Query Parameters:
    - start_date: Filter anomalies from this date (optional)
    - end_date: Filter anomalies until this date (optional)
    - severity: Filter by severity level (CRITICAL, HIGH, MEDIUM, LOW)
    
    Returns:
    - List of anomaly alerts with transaction details, anomaly scores, severity
    - Severity breakdown statistics
    
    Example:
    - GET /api/v1/analytics/anomalies/revenue?start_date=2024-11-01&severity=HIGH
    
    Notes:
    - Anomalies detected daily by Airflow ML pipeline
    - Data source: sme_lake.gold.ml_anomaly_alerts (Trino)
    - Model: Isolation Forest trained on bank transaction features
    - Severity levels: CRITICAL (score < -1.0), HIGH (-0.75), MEDIUM (-0.5), LOW (> -0.5)
    """
    try:
        logger.info(f"Fetching revenue anomalies for org_id={current_user.org_id}, severity={severity}")
        
        # Validate severity if provided
        if severity:
            valid_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            if severity.upper() not in valid_severities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity. Must be one of: {valid_severities}"
                )
        
        # Query anomaly data from Trino Gold layer
        anomaly_data = await service.get_revenue_anomalies(
            db=db,
            org_id=current_user.org_id,
            start_date=start_date,
            end_date=end_date,
            severity=severity,
        )
        
        # Calculate severity breakdown
        severity_counts = {}
        for item in anomaly_data:
            sev = item.get("severity", "UNKNOWN")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        return AnomalyResponse(
            data=anomaly_data,
            total_anomalies=len(anomaly_data),
            severity_breakdown=severity_counts,
            timestamp=datetime.utcnow(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching revenue anomalies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve revenue anomalies: {str(e)}"
        )

