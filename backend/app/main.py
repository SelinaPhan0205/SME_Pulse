"""FastAPI Application Entry Point"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
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

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup: Initialize database schemas
    await initialize_database_schemas()
    yield
    # Shutdown: Cleanup resources
    pass


app = FastAPI(
    title="SME Pulse Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add Security Middlewares
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
if settings.BACKEND_RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(SMEPulseException)
async def sme_pulse_exception_handler(request: Request, exc: SMEPulseException):
    """Handle custom SME Pulse exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.__class__.__name__},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "error_code": "ValidationError"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error_code": "InternalServerError"},
    )


# Include Routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/v1", tags=["User Management"])
app.include_router(customers_router, prefix="/api/v1", tags=["Customers"])
app.include_router(suppliers_router, prefix="/api/v1", tags=["Suppliers"])
app.include_router(accounts_router, prefix="/api/v1", tags=["Accounts"])
app.include_router(finance_router, prefix="/api/v1", tags=["Finance"])
app.include_router(bills_router, prefix="/api/v1", tags=["AP Bills"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(settings_router, prefix="/api/v1", tags=["Settings"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SME Pulse Backend",
        "version": "1.0.0",
        "environment": settings.BACKEND_ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """Kubernetes/Docker health probe"""
    return {"status": "ok"}
