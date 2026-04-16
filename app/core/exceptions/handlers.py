"""
Global exception handlers for the FastAPI application.

These handlers catch exceptions and return properly formatted JSON responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import traceback

from .base import AppException
from app.core.logging.logger import add_to_log


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    
    add_to_log(
        "error" if exc.status_code >= 500 else "info",
        f"Application exception: {exc.message}",
        path=str(request.url),
        status_code=exc.status_code,
        details=exc.details
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url.path)
        }
    )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    
    add_to_log(
        "info",
        "Validation error",
        path=str(request.url),
        errors=exc.errors()
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation failed",
            "details": {"validation_errors": exc.errors()},
            "path": str(request.url.path)
        }
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    
    add_to_log(
        "error",
        f"Database error: {str(exc)}",
        path=str(request.url),
        error_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Database operation failed",
            "details": {},
            "path": str(request.url.path)
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    
    error_trace = traceback.format_exc()
    
    add_to_log(
        "error",
        f"Unhandled exception: {str(exc)}",
        path=str(request.url),
        error_type=type(exc).__name__,
        traceback=error_trace
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "An unexpected error occurred",
            "details": {},
            "path": str(request.url.path)
        }
    )
