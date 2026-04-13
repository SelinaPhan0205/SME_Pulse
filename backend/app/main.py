"""Điểm vào FastAPI ứng dụng"""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.exceptions import SMEPulseException
from app.core.logging_config import setup_logging
from app.db.init_db import initialize_database_schemas
from app.middleware.security import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
)
from app.modules.auth.router import router as auth_router
from app.modules.partners.router import customers_router, suppliers_router
from app.modules.finance import finance_router, accounts_router, bills_router
from app.modules.analytics.router import router as analytics_router
from app.modules.users.router import router as users_router
from app.modules.settings.router import router as settings_router

# Thiết lập logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Các sự kiện vòng đời ứng dụng"""
    settings.validate_security_settings()
    logger.info("Backend runtime configuration", extra=settings.runtime_summary())

    # Khởi động: Khởi tạo schema cơ sở dữ liệu
    await initialize_database_schemas()
    yield
    # Tắt: Dọn dẹp tài nguyên
    pass


app = FastAPI(
    title="SME Pulse Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Thêm Middleware bảo mật
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
if settings.BACKEND_RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Trình xử lý ngoại lệ
@app.exception_handler(SMEPulseException)
async def sme_pulse_exception_handler(request: Request, exc: SMEPulseException):
    """Xử lý các ngoại lệ tùy chỉnh SME Pulse"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.__class__.__name__},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Xử lý lỗi xác thực"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(exc.errors()), "error_code": "ValidationError"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Xử lý tất cả các ngoại lệ khác"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Lỗi máy chủ nội bộ", "error_code": "InternalServerError"},
    )


# Bao gồm Routers
app.include_router(auth_router, prefix="/auth", tags=["Xác thực"])
app.include_router(users_router, prefix="/api/v1", tags=["Quản lý người dùng"])
app.include_router(customers_router, prefix="/api/v1", tags=["Khách hàng"])
app.include_router(suppliers_router, prefix="/api/v1", tags=["Nhà cung cấp"])
app.include_router(accounts_router, prefix="/api/v1", tags=["Tài khoản"])
app.include_router(finance_router, prefix="/api/v1", tags=["Tài chính"])
app.include_router(bills_router, prefix="/api/v1", tags=["Hóa đơn AP"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Phân tích"])
app.include_router(settings_router, prefix="/api/v1", tags=["Cài đặt"])


@app.get("/")
async def root():
    """Kiểm tra sức khỏe endpoint"""
    return {
        "status": "healthy",
        "service": "SME Pulse Backend",
        "version": "1.0.0",
        "environment": settings.BACKEND_ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """Kiểm tra sức khỏe Kubernetes/Docker"""
    return {"status": "ok"}
