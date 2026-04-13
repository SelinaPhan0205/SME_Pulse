"""Mô-đun Phân tích - API KPI thực tế và báo cáo."""

from app.modules.analytics.router import router as analytics_router
from app.modules.analytics import tasks  # Đăng ký các tác vụ Celery

__all__ = ["analytics_router", "tasks"]
