"""Cấu hình Celery cho các công việc nền"""

from celery import Celery
from app.core.config import settings

# Tạo ứng dụng Celery
celery_app = Celery(
    "sme_pulse",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
)

# Cấu hình Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # Giới hạn cứng 30 phút
    task_soft_time_limit=25 * 60,  # Giới hạn mềm 25 phút
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Tự động phát hiện công việc từ các mô-đun
celery_app.autodiscover_tasks(['app.modules.analytics'])
