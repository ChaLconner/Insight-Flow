"""
Standardized exceptions for Insight-Flow.
"""

from typing import Any


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ResourceNotFound(AppError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(message, code="RESOURCE_NOT_FOUND", status_code=404, details=details)


class BadRequest(AppError):
    """Raised when the request is invalid."""

    def __init__(self, message: str = "Bad request", details: dict[str, Any] | None = None):
        super().__init__(message, code="BAD_REQUEST", status_code=400, details=details)


class Unauthorized(AppError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Unauthorized", details: dict[str, Any] | None = None):
        super().__init__(message, code="UNAUTHORIZED", status_code=401, details=details)


class Forbidden(AppError):
    """Raised when permission is denied."""

    def __init__(self, message: str = "Forbidden", details: dict[str, Any] | None = None):
        super().__init__(message, code="FORBIDDEN", status_code=403, details=details)


class Conflict(AppError):
    """Raised when a resource conflict occurs (e.g. duplicate)."""

    def __init__(self, message: str = "Conflict", details: dict[str, Any] | None = None):
        super().__init__(message, code="CONFLICT", status_code=409, details=details)
