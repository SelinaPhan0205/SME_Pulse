"""Router Phân tích - API KPI thực tế và báo cáo."""

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
# BẢNG ĐIỀU KHIỂN & ĐIỂM KPI
# ============================================================

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy tóm tắt KPI bảng điều khiển hoàn chỉnh.
    
    **UC08 - Bảng điều khiển**
    
    Trả lại:
    - DSO, DPO, CCC, Tổng AR/AP, Số dư Tiền mặt, Vốn lưu động
    - Số lượng hóa đơn/hợp đồng quá hạn và số tiền
    - Dữ liệu thực tế từ Application DB
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
# BÁO CÁO LÃO HÓA
# ============================================================

@router.get("/aging/ar", response_model=ARAgingResponse)
async def get_ar_aging(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy báo cáo lão hóa AR (Công nợ Phải thu).
    
    **UC05 - Công nợ AR**
    
    Trả lại:
    - Tổng số AR và số lượng hóa đơn
    - Phân tích theo các khoảng lão hóa: 0-30, 31-60, 61-90, >90 ngày
    - Số tiền và số lượng cho mỗi khoảng
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
    Lấy báo cáo lão hóa AP (Công nợ Phải trả).
    
    **UC06 - Công nợ AP**
    
    Trả lại:
    - Tổng số AP và số lượng hợp đồng
    - Phân tích theo các khoảng lão hóa: 0-30, 31-60, 61-90, >90 ngày
    - Số tiền và số lượng cho mỗi khoảng
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
# ĐIỂM KPI
# ============================================================

@router.get("/kpi/daily-revenue", response_model=DailyRevenueResponse)
async def get_daily_revenue(
    days: int = Query(7, ge=1, le=90, description="Number of days to retrieve"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy KPI doanh thu hàng ngày cho N ngày gần đây.
    
    **UC08 - Bảng điều khiển (biểu đồ nhỏ)**
    
    Tham số truy vấn:
    - days: Số ngày (mặc định: 7, tối đa: 90)
    
    Trả lại:
    - Tổng doanh thu, doanh thu trung bình hàng ngày
    - Phân tích hàng ngày với ngày tháng và số tiền
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
    Lấy KPI tỷ lệ thanh toán thành công cho N ngày gần đây.
    
    **UC08 - Bảng điều khiển (biểu đồ nhỏ)**
    **UC05 - Thanh toán (Thẻ Điều hòa)**
    
    Tham số truy vấn:
    - days: Số ngày (mặc định: 7, tối đa: 90)
    
    Trả lại:
    - Phần trăm tỷ lệ thành công
    - Tổng giao dịch, số lượng thành công, số lượng thất bại
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
    Lấy trạng thái điều hòa thanh toán cho một ngày cụ thể.
    
    **UC05 - Thanh toán (Thẻ Điều hòa)**
    
    Tham số truy vấn:
    - reconcile_date: Ngày cần điều hòa (mặc định: hôm nay, định dạng: YYYY-MM-DD)
    
    Trả lại:
    - Tổng giao dịch, số lượng đã điều hòa, số lượng đang chờ xử lý
    - Phần trăm tỷ lệ điều hòa
    - Danh sách các chênh lệch
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
# ĐIỂM CUỐI HÀNH ĐỘNG ĐIỀU HÒA
# ============================================================

@router.post("/reconciliation/auto-match", response_model=ReconciliationAutoMatchResponse)
async def auto_match_transactions(
    reconcile_date: Optional[date] = Query(None, description="Date to reconcile (default: today)"),
    tolerance: float = Query(1000.0, ge=0, description="Amount tolerance in VND for matching"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tự động khớp các giao dịch ngân hàng với các khoản thanh toán hệ thống.
    
    **UC05 - Điều hòa Thanh toán**
    
    Thuật toán:
    1. Lấy tất cả các giao dịch ngân hàng cho ngày hôm đó
    2. Lấy tất cả các khoản thanh toán hệ thống cho ngày hôm đó
    3. Khớp theo số tiền trong giới hạn dung sai (±dung_sai VND)
    4. Trả lại các cặp đã khớp và giao dịch không khớp
    
    Tham số truy vấn:
    - reconcile_date: Ngày cần điều hòa (mặc định: hôm nay)
    - tolerance: Dung sai số tiền cho khớp (mặc định: 1000 VND)
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
    Xác nhận khớp điều hòa giữa giao dịch ngân hàng và khoản thanh toán.
    
    **UC05 - Xác nhận Điều hòa Thủ công**
    
    Tham số đường dẫn:
    - transaction_id: ID Giao dịch ngân hàng cần xác nhận
    
    Phần thân yêu cầu:
    - bank_transaction_id: ID Giao dịch ngân hàng
    - payment_id: ID Khoản thanh toán hệ thống cần khớp
    - notes: Ghi chú tùy chọn cho đường audit
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
    Từ chối một gợi ý khớp điều hòa.
    
    **UC05 - Từ chối Điều hòa**
    
    Tham số đường dẫn:
    - transaction_id: ID Giao dịch ngân hàng để từ chối gợi ý khớp
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
    Lấy danh sách các giao dịch không khớp/chờ xử lý để điều hòa.
    
    **UC05 - Xem Điều hòa Chờ xử lý**
    
    Trả lại các giao dịch chưa được khớp.
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
# ĐIỂM CUỐI XUẤT
# ============================================================

@router.post("/reports/export", response_model=ExportJobResponse, status_code=202)
async def export_report(
    report_type: str = Query(..., description="ar_aging, ap_aging, cashflow"),
    format: str = Query("xlsx", description="xlsx only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tạo công việc xuất không đồng bộ để tạo báo cáo.
    
    **BƯỚC 4 - Công nhân xuất Excel**
    
    Tham số truy vấn:
    - report_type: ar_aging, ap_aging, hoặc cashflow
    - format: xlsx (mặc định)
    
    Trả lại:
    - job_id: Sử dụng để kiểm tra trạng thái qua GET /reports/jobs/{job_id}
    - status: pending (xử lý trong nền)
    
    Ghi chú:
    - Xuất được xử lý không đồng bộ (5-30 giây)
    - Kiểm tra trạng thái công việc để lấy URL tải xuống
    - URL tải xuống hết hạn sau 48 giờ
    """
    try:
        # Xác thực report_type
        valid_types = ["ar_aging", "ap_aging", "cashflow"]
        if report_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report_type. Must be one of: {valid_types}"
            )
        
        # Xác thực định dạng
        if format != "xlsx":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only xlsx format is supported"
            )
        
        # Định tuyến tới tác vụ Celery chính xác (lấy task_id từ Celery)
        if report_type == "ar_aging":
            celery_task = tasks.export_ar_aging.delay(current_user.org_id)
        elif report_type == "ap_aging":
            celery_task = tasks.export_ap_aging.delay(current_user.org_id)
        elif report_type == "cashflow":
            celery_task = tasks.export_cashflow_forecast.delay(current_user.org_id)
        
        # Sử dụng ID tác vụ Celery làm job_id
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
    Kiểm tra trạng thái công việc xuất và lấy URL tải xuống.
    
    **BƯỚC 4 - Công nhân xuất Excel**
    
    Tham số đường dẫn:
    - job_id: ID Công việc từ POST /reports/export
    
    Trả lại:
    - status: pending → processing → completed (hoặc failed)
    - file_url: Liên kết tải xuống (hết hạn 48h)
    - progress: 0-100%
    
    Chiến lược thăm dò:
    - Pending: Thử lại mỗi 2-5 giây
    - Processing: Thử lại mỗi 1-2 giây
    - Completed: Sử dụng file_url để tải xuống
    - Failed: Kiểm tra error_message để biết chi tiết
    """
    try:
        # Lấy kết quả tác vụ Celery
        task_result = AsyncResult(job_id, app=celery_app)
        
        # Ánh xạ trạng thái Celery tới các trạng thái của chúng tôi
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
            report_type="ar_aging",  # Mặc định, sẽ được theo dõi nếu lưu trữ trong DB
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
# ĐIỂM CUỐI NHÚNG METABASE
# ============================================================

@router.get("/metabase-token", response_model=MetabaseTokenResponse)
async def get_metabase_token(
    resource_id: int = Query(..., description="Metabase resource ID (dashboard or question)"),
    resource_type: str = Query("dashboard", description="Resource type: 'dashboard' or 'question'"),
    current_user: User = Depends(get_current_user),
):
    """
    Tạo token JWT để nhúng bảng điều khiển/câu hỏi Metabase.
    
    **UC03 - Nhúng Metabase**
    
    Tham số truy vấn:
    - resource_id: ID tài nguyên Metabase (ví dụ: 2, 5)
    - resource_type: Loại tài nguyên - 'dashboard' hoặc 'question' (mặc định: dashboard)
    
    Bảng điều khiển có sẵn:
    - resource_id=2 → Bảng điều khiển Dự báo Dòng tiền
    - resource_id=5 → Bảng điều khiển Cảnh báo Bất thường
    
    Trả lại:
    - token: Token JWT để nhúng
    - embed_url: URL đầy đủ cho thuộc tính src của iframe
    - resource_id: ID tài nguyên được yêu cầu
    - expires_in: Thời gian hết hạn token tính bằng giây
    
    Sử dụng trong Frontend:
    ```javascript
    // Lấy token cho Bảng điều khiển Dự báo Dòng tiền
    const response = await fetch('/api/v1/analytics/metabase-token?resource_id=2');
    const data = await response.json();
    
    // Nhúng trong iframe
    <iframe src={data.embed_url} frameBorder="0" width="100%" height="800" />
    ```
    
    Ghi chú:
    - Token có hiệu lực trong 10 phút (600 giây)
    - Mỗi yêu cầu tạo một token mới
    - Token được ký bằng khóa bí mật nhúng Metabase
    - Hoạt động cho cả bảng điều khiển và câu hỏi (truy vấn)
    """
    try:
        import hashlib
        import hmac
        import base64
        
        # Xác thực resource_type
        if resource_type not in ["dashboard", "question"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="resource_type must be 'dashboard' or 'question'"
            )
        
        # Tạo payload cho JWT
        payload = {
            "resource": {resource_type: resource_id},
            "params": {"user_id": current_user.id, "org_id": current_user.org_id},
            "iat": int(time.time()),
            "exp": int(time.time()) + settings.METABASE_TOKEN_EXPIRE_SECONDS,
        }
        
        # Mã hóa JWT sử dụng HMAC với khóa bí mật
        # Metabase sử dụng thuật toán HS256
        secret = settings.METABASE_EMBEDDING_SECRET_KEY
        
        # Tạo JWT thủ công để tương thích với Metabase
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Tạo chữ ký
        message = f"{header}.{payload_str}"
        signature = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        ).decode().rstrip('=')
        
        token = f"{message}.{signature}"
        
        # Xây dựng URL nhúng dựa trên loại tài nguyên
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
# ĐIỂM CUỐI DỰ BÁO ML & PHÁT HIỆN BẤT THƯỜNG
# ============================================================

@router.get("/forecast/revenue", response_model=ForecastResponse)
async def get_forecast_revenue(
    start_date: Optional[date] = Query(None, description="Filter forecasts from this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter forecasts until this date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Nhận dự đoán dự báo doanh thu từ mô hình ML Prophet.
    
    **UC09 - Dự báo Dòng tiền**
    
    Tham số truy vấn:
    - start_date: Lọc dự báo từ ngày này (không bắt buộc)
    - end_date: Lọc dự báo cho đến ngày này (không bắt buộc)
    
    Trả lại:
    - Danh sách các điểm dữ liệu dự báo với dòng tiền dự đoán, giới hạn tự tin
    - Thông tin siêu dữ liệu mô hình (tên, dấu thời gian dự đoán)
    
    Ví dụ:
    - GET /api/v1/analytics/forecast/revenue?start_date=2024-12-01&end_date=2024-12-31
    
    Ghi chú:
    - Dự báo được tạo hàng ngày bởi đường ống ML Airflow
    - Nguồn dữ liệu: sme_lake.gold.ml_cashflow_forecast (Trino)
    - Mô hình: Prophet v1 được đào tạo trên dữ liệu dòng tiền lịch sử
    """
    try:
        logger.info(f"Fetching revenue forecast for org_id={current_user.org_id}, dates={start_date} to {end_date}")
        
        # Truy vấn dữ liệu dự báo từ lớp Gold Trino
        forecast_data = await service.get_revenue_forecast(
            db=db,
            org_id=current_user.org_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Tính toán phân tích mức độ nghiêm trọng
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
    Nhận cảnh báo phát hiện bất thường doanh thu từ mô hình ML Isolation Forest.
    
    **UC10 - Phát hiện Bất thường**
    
    Tham số truy vấn:
    - start_date: Lọc bất thường từ ngày này (không bắt buộc)
    - end_date: Lọc bất thường cho đến ngày này (không bắt buộc)
    - severity: Lọc theo mức độ nghiêm trọng (CRITICAL, HIGH, MEDIUM, LOW)
    
    Trả lại:
    - Danh sách cảnh báo bất thường với chi tiết giao dịch, điểm bất thường, mức độ nghiêm trọng
    - Thống kê phân tích mức độ nghiêm trọng
    
    Ví dụ:
    - GET /api/v1/analytics/anomalies/revenue?start_date=2024-11-01&severity=HIGH
    
    Ghi chú:
    - Bất thường được phát hiện hàng ngày bởi đường ống ML Airflow
    - Nguồn dữ liệu: sme_lake.gold.ml_anomaly_alerts (Trino)
    - Mô hình: Isolation Forest được đào tạo trên các tính năng giao dịch ngân hàng
    - Mức độ nghiêm trọng: CRITICAL (điểm < -1.0), HIGH (-0.75), MEDIUM (-0.5), LOW (> -0.5)
    """
    try:
        logger.info(f"Fetching revenue anomalies for org_id={current_user.org_id}, severity={severity}")
        
        # Xác thực mức độ nghiêm trọng nếu được cung cấp
        if severity:
            valid_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            if severity.upper() not in valid_severities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity. Must be one of: {valid_severities}"
                )
        
        # Truy vấn dữ liệu bất thường từ lớp Gold Trino
        anomaly_data = await service.get_revenue_anomalies(
            db=db,
            org_id=current_user.org_id,
            start_date=start_date,
            end_date=end_date,
            severity=severity,
        )
        
        # Tính toán phân tích mức độ nghiêm trọng
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

