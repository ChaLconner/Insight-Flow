"""
Standardized API response utilities.
Provides consistent response format across all API endpoints.
"""
from typing import Any, Optional, List, Dict, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi import status

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    All API responses should use this format for consistency.
    """
    success: bool = Field(description="Whether the request was successful")
    message: Optional[str] = Field(default=None, description="Human-readable message")
    data: Optional[T] = Field(default=None, description="Response data payload")
    errors: Optional[List[Dict[str, Any]]] = Field(default=None, description="Validation or error details")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PaginatedResponse(APIResponse[T], Generic[T]):
    """
    Paginated API response for list endpoints.
    """
    pagination: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pagination information"
    )
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        size: int,
        message: Optional[str] = None
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        has_more = (page * size) < total
        total_pages = (total + size - 1) // size if size > 0 else 0
        
        return cls(
            success=True,
            message=message,
            data=items,
            pagination={
                "total": total,
                "page": page,
                "size": size,
                "totalPages": total_pages,
                "hasMore": has_more,
                "hasNext": page < total_pages,
                "hasPrevious": page > 1
            }
        )


# Helper functions for creating responses

def success_response(
    data: Any = None,
    message: str = "Success",
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    Create a successful API response.
    
    Args:
        data: Response data payload
        message: Human-readable success message
        meta: Additional metadata
        status_code: HTTP status code
    
    Returns:
        JSONResponse with standardized format
    """
    response_data = {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if meta:
        response_data["meta"] = meta
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


def error_response(
    message: str,
    code: str = "ERROR",
    errors: Optional[List[Dict[str, Any]]] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """
    Create an error API response.
    
    Args:
        message: Human-readable error message
        code: Error code for programmatic handling
        errors: List of detailed errors (e.g., validation errors)
        details: Additional error details
        status_code: HTTP status code
    
    Returns:
        JSONResponse with standardized error format
    """
    response_data = {
        "success": False,
        "message": message,
        "code": code,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if errors:
        response_data["errors"] = errors
    
    if details:
        response_data["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


def created_response(
    data: Any,
    message: str = "Resource created successfully"
) -> JSONResponse:
    """Create a 201 Created response."""
    return success_response(
        data=data,
        message=message,
        status_code=status.HTTP_201_CREATED
    )


def no_content_response() -> JSONResponse:
    """Create a 204 No Content response."""
    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None
    )


def not_found_response(
    message: str = "Resource not found",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None
) -> JSONResponse:
    """Create a 404 Not Found response."""
    details = {}
    if resource_type:
        details["resource_type"] = resource_type
    if resource_id:
        details["resource_id"] = resource_id
    
    return error_response(
        message=message,
        code="NOT_FOUND",
        details=details if details else None,
        status_code=status.HTTP_404_NOT_FOUND
    )


def unauthorized_response(
    message: str = "Authentication required"
) -> JSONResponse:
    """Create a 401 Unauthorized response."""
    return error_response(
        message=message,
        code="UNAUTHORIZED",
        status_code=status.HTTP_401_UNAUTHORIZED
    )


def forbidden_response(
    message: str = "You don't have permission to perform this action"
) -> JSONResponse:
    """Create a 403 Forbidden response."""
    return error_response(
        message=message,
        code="FORBIDDEN",
        status_code=status.HTTP_403_FORBIDDEN
    )


def validation_error_response(
    errors: List[Dict[str, Any]],
    message: str = "Validation failed"
) -> JSONResponse:
    """Create a 422 Validation Error response."""
    return error_response(
        message=message,
        code="VALIDATION_ERROR",
        errors=errors,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


def conflict_response(
    message: str = "Resource already exists",
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create a 409 Conflict response."""
    return error_response(
        message=message,
        code="CONFLICT",
        details=details,
        status_code=status.HTTP_409_CONFLICT
    )


def internal_error_response(
    error_id: Optional[str] = None,
    message: str = "An unexpected error occurred"
) -> JSONResponse:
    """Create a 500 Internal Server Error response."""
    details = {}
    if error_id:
        details["error_id"] = error_id
    
    return error_response(
        message=message,
        code="INTERNAL_ERROR",
        details=details if details else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
