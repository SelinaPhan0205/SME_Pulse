"""Analytics module - Real-time KPI and reporting APIs."""

from app.modules.analytics.router import router as analytics_router
from app.modules.analytics import tasks  # Register Celery tasks

__all__ = ["analytics_router", "tasks"]
