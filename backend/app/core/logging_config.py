"""Cấu hình ghi nhật ký với đầu ra JSON có cấu trúc."""

import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Trình định dạng JSON tùy chỉnh để ghi nhật ký có cấu trúc.
    Xuất các bản ghi ở định dạng JSON để dễ dàng phân tích cú pháp bởi các công cụ tổng hợp nhật ký.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Thêm các trường bổ sung (ví dụ: request_id, user_id)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "org_id"):
            log_data["org_id"] = record.org_id
        
        # Thêm các trường bổ sung tùy chỉnh
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info"
            ]:
                log_data[key] = value
        
        # Thêm thông tin ngoại lệ
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging():
    """
    Cấu hình ghi nhật ký ứng dụng.
    
    - Định dạng JSON cho sản xuất (dễ phân tích)
    - Định dạng văn bản cho phát triển (dễ đọc bởi con người)
    - Xuất ra cả bằng điều khiển và tệp
    """
    # Tạo thư mục logs nếu nó không tồn tại
    log_file = Path(settings.BACKEND_LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Trình ghi nhật ký gốc
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.BACKEND_LOG_LEVEL)
    
    # Xóa các trình xử lý hiện có
    root_logger.handlers.clear()
    
    # Trình xử lý bằng điều khiển
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.BACKEND_LOG_LEVEL)
    
    # Trình xử lý tệp
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(settings.BACKEND_LOG_LEVEL)
    
    # Format dựa trên cấu hình
    if settings.BACKEND_LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Thêm các trình xử lý
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Triệt tiêu các trình ghi nhật ký ồn ào
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    logging.info(
        "Logging configured",
        extra={
            "log_level": settings.BACKEND_LOG_LEVEL,
            "log_format": settings.BACKEND_LOG_FORMAT,
            "log_file": str(log_file),
            "environment": settings.BACKEND_ENVIRONMENT,
        }
    )
