"""Service Xuất - Xử lý công việc xuất dưới nền."""

import logging
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analytics import ExportJob

logger = logging.getLogger(__name__)


async def create_export_job(
    db: AsyncSession,
    org_id: int,
    report_type: str,
    format: str = "xlsx",
    date_from: str = None,
    date_to: str = None
) -> str:
    """
    Tạo công việc xuất và trả về job_id.
    
    Đối số:
        db: Phiên cơ sở dữ liệu
        org_id: ID Tổ chức
        report_type: ar_aging, ap_aging, cashflow, payment
        format: xlsx hoặc pdf
        date_from: Ngày bắt đầu tùy chọn (YYYY-MM-DD)
        date_to: Ngày kết thúc tùy chọn (YYYY-MM-DD)
    
    Trả lại:
        job_id để theo dõi
    """
    try:
        public_job_id = f"exp_{uuid.uuid4().hex[:12]}"
        
        # Tạo record ExportJob với ID tự động tăng, nhưng lưu trữ job_id công khai trong trường job_id
        job = ExportJob(
            job_id=public_job_id,
            org_id=org_id,
            job_type=report_type,
            status="pending",
            file_url=None,
            error_log=None,
            job_metadata={
                "format": format,
                "date_from": date_from,
                "date_to": date_to
            }
        )
        
        db.add(job)
        await db.commit()
        
        logger.info(f"Created export job {public_job_id} for org_id={org_id}, type={report_type}")
        return public_job_id
        
    except Exception as e:
        logger.error(f"Error creating export job: {e}")
        await db.rollback()
        raise


async def get_job_status(
    db: AsyncSession,
    job_id: str,
    org_id: int
) -> dict:
    """Lấy trạng thái công việc xuất."""
    try:
        query = select(ExportJob).where(
            ExportJob.job_id == job_id,
            ExportJob.org_id == org_id
        )
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        return {
            "job_id": job.job_id,
            "status": job.status,
            "report_type": job.job_type,
            "format": job.job_metadata.get("format", "xlsx") if job.job_metadata else "xlsx",
            "file_url": job.file_url,
            "error_message": job.error_log,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    file_url: str = None,
    error_log: str = None
) -> None:
    """Cập nhật trạng thái công việc xuất."""
    try:
        query = select(ExportJob).where(ExportJob.job_id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if job:
            job.status = status
            if file_url:
                job.file_url = file_url
            if error_log:
                job.error_log = error_log
            job.updated_at = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Updated job {job_id} status to {status}")
            
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        await db.rollback()
        raise
