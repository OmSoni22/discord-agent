"""
Custom exception classes for the application.

These exceptions provide structured error responses with proper HTTP status codes.
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base exception for all application exceptions."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """Raised when a resource is not found."""
    
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} with id '{identifier}' not found",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)}
        )


class ValidationException(AppException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=422,
            details={"validation_errors": errors or {}}
        )


class ConflictException(AppException):
    """Raised when there's a conflict (e.g., duplicate entry)."""
    
    def __init__(self, message: str):
        super().__init__(message=message, status_code=409)


class UnauthorizedException(AppException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message, status_code=401)


class ForbiddenException(AppException):
    """Raised when user lacks permission."""
    
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message=message, status_code=403)


class DatabaseException(AppException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message=message, status_code=500)
