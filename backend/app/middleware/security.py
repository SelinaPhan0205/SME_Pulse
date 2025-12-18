"""Security middleware for request tracking and rate limiting."""

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
    Add request ID and timing to all requests.
    Useful for request tracing and performance monitoring.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Track request timing
        start_time = time.time()
        
        # Add request ID to response headers
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request
        logger.info(
            f"Request completed",
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
    Add security headers to all responses.
    Protects against common web vulnerabilities.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.
    Limits login attempts to prevent brute force attacks.
    
    For production: Use Redis-based rate limiting (e.g., slowapi, redis)
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
        self.paths = paths or ["/auth/login"]  # Protect login by default
        
        # In-memory storage: {ip: [(timestamp, count), ...]}
        self.requests = defaultdict(list)
    
    def _clean_old_requests(self, ip: str, now: datetime):
        """Remove requests older than the time window."""
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests[ip] = [
            (ts, count) for ts, count in self.requests[ip]
            if ts > cutoff
        ]
    
    def _get_request_count(self, ip: str, now: datetime) -> int:
        """Get total request count within the time window."""
        self._clean_old_requests(ip, now)
        return sum(count for _, count in self.requests[ip])
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only rate limit specific paths
        if request.url.path not in self.paths:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.now()
        
        # Check rate limit
        request_count = self._get_request_count(client_ip, now)
        
        if request_count >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "request_count": request_count,
                    "max_requests": self.max_requests,
                }
            )
            # Return 429 response directly (don't raise HTTPException in middleware)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too many requests",
                    "detail": f"Rate limit exceeded. Please try again in {self.window_seconds} seconds.",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )
        
        # Record this request
        self.requests[client_ip].append((now, 1))
        
        return await call_next(request)
