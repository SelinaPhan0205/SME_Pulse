"""Các ngoại lệ tùy chỉnh và trình xử lý ngoại lệ."""

import logging
from typing import Union

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class SMEPulseException(Exception):
    """Ngoại lệ cơ sở cho ứng dụng SME Pulse."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: dict = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class AuthenticationError(SMEPulseException):
    """Xác thực thất bại - thông tin đăng nhập không hợp lệ."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(SMEPulseException):
    """Ủy quyền thất bại - quyền không đủ."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ResourceNotFoundError(SMEPulseException):
    """Tài nguyên không tìm thấy."""
    
    def __init__(self, resource: str, identifier: Union[int, str]):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"resource": resource, "identifier": str(identifier)}
        )


class ValidationError(SMEPulseException):
    """Lỗi xác thực logic kinh doanh."""
    
    def __init__(self, message: str, errors: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors or {}}
        )


class DatabaseError(SMEPulseException):
    """Lỗi hoạt động Database."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

async def sme_pulse_exception_handler(
    request: Request,
    exc: SMEPulseException
) -> JSONResponse:
    """
    Xử lý các ngoại lệ tùy chỉnh SME Pulse.
    Trả về phản hồi lỗi có cấu trúc.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"SMEPulseException: {exc.message}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "path": request.url.path,
            "detail": exc.detail,
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "request_id": request_id,
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Xử lý lỗi xác thực Pydantic (422).
    Cung cấp lỗi xác thực chi tiết ở cấp độ trường.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Trích xuất lỗi xác thực
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": list(error["loc"]),
            "msg": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        f"Validation error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "errors": errors,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": errors,
            "request_id": request_id,
        }
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """
    Xử lý lỗi Database của SQLAlchemy.
    Ghi lại đầy đủ lỗi nhưng trả về thông báo chung cho client.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database operation failed",
            "detail": "An error occurred while processing your request.",
            "request_id": request_id,
        }
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Trình xử lý bắt tất cả cho các ngoại lệ không mong muốn.
    Ghi lại đầy đủ lỗi nhưng trả về thông báo chung cho client.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        }
    )
