"""Middleware bảo mật cho theo dõi yêu cầu và giới hạn tốc độ."""

import time
import uuid
import logging
from typing import Callable
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Thêm ID yêu cầu và thời gian vào tất cả các yêu cầu.
    Hữu ích cho theo dõi yêu cầu và giám sát hiệu suất.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Tạo ID yêu cầu duy nhất
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Theo dõi thời gian yêu cầu
        start_time = time.time()
        
        # Thêm ID yêu cầu vào header phản hồi
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Ghi nhật ký yêu cầu
        logger.info(
            f"Yêu cầu đã hoàn thành",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Thêm header bảo mật vào tất cả các phản hồi.
    Bảo vệ chống lại các lỗ hổng web phổ biến.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Header bảo mật
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Giới hạn tốc độ trong bộ nhớ đơn giản.
    Giới hạn các cố gắng đăng nhập để ngăn chặn các cuộc tấn công brute force.
    
    Để sản xuất: Sử dụng giới hạn tốc độ dựa trên Redis (ví dụ: slowapi, redis)
    """
    
    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 5,
        window_seconds: int = 60,
        paths: list = None
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.paths = paths or ["/auth/login"]  # Bảo vệ đăng nhập theo mặc định
        
        # Lưu trữ trong bộ nhớ: {ip: [(timestamp, count), ...]}
        self.requests = defaultdict(list)
    
    def _clean_old_requests(self, ip: str, now: datetime):
        """Xóa các yêu cầu cũ hơn cửa sổ thời gian."""
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests[ip] = [
            (ts, count) for ts, count in self.requests[ip]
            if ts > cutoff
        ]
    
    def _get_request_count(self, ip: str, now: datetime) -> int:
        """Nhận tổng số lượng yêu cầu trong cửa sổ thời gian."""
        self._clean_old_requests(ip, now)
        return sum(count for _, count in self.requests[ip])
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Chỉ giới hạn tốc độ các đường dẫn cụ thể
        if request.url.path not in self.paths:
            return await call_next(request)
        
        # Lấy IP khách hàng
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.now()
        
        # Kiểm tra giới hạn tốc độ
        request_count = self._get_request_count(client_ip, now)
        
        if request_count >= self.max_requests:
            logger.warning(
                f"Giới hạn tốc độ vượt quá",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "request_count": request_count,
                    "max_requests": self.max_requests,
                }
            )
            # Trả về phản hồi 429 trực tiếp (không tăng HTTPException trong middleware)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Quá nhiều yêu cầu",
                    "detail": f"Giới hạn tốc độ vượt quá. Vui lòng thử lại trong {self.window_seconds} giây.",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )
        
        # Ghi lại yêu cầu này
        self.requests[client_ip].append((now, 1))
        
        return await call_next(request)
