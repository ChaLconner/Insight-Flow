"""
Comprehensive tests for utils/exceptions.py

Tests follow best practices:
- Arrange-Act-Assert pattern
- One assertion per test (where practical)
- Descriptive test names
- Test edge cases
"""

import pytest
from utils.exceptions import (
    AppError,
    ResourceNotFound,
    BadRequest,
    Unauthorized,
    Forbidden,
    Conflict,
)


class TestAppError:
    """Tests for the base AppError exception class."""
    
    def test_app_error_default_values(self):
        """Test AppError initializes with correct default values."""
        # Arrange & Act
        error = AppError("Something went wrong")
        
        # Assert
        assert error.message == "Something went wrong"
        assert error.code == "INTERNAL_ERROR"
        assert error.status_code == 500
        assert error.details is None
    
    def test_app_error_custom_values(self):
        """Test AppError accepts custom code, status_code, and details."""
        # Arrange
        details = {"field": "email", "reason": "invalid"}
        
        # Act
        error = AppError(
            message="Custom error",
            code="CUSTOM_ERROR",
            status_code=418,
            details=details
        )
        
        # Assert
        assert error.message == "Custom error"
        assert error.code == "CUSTOM_ERROR"
        assert error.status_code == 418
        assert error.details == details
    
    def test_app_error_inherits_from_exception(self):
        """Test AppError can be raised and caught as Exception."""
        # Arrange & Act & Assert
        with pytest.raises(Exception) as exc_info:
            raise AppError("Test error")
        
        assert str(exc_info.value) == "Test error"
    
    def test_app_error_str_representation(self):
        """Test AppError string representation is the message."""
        # Arrange & Act
        error = AppError("Error message")
        
        # Assert
        assert str(error) == "Error message"


class TestResourceNotFound:
    """Tests for ResourceNotFound exception."""
    
    def test_resource_not_found_default_message(self):
        """Test ResourceNotFound has correct default message."""
        # Act
        error = ResourceNotFound()
        
        # Assert
        assert error.message == "Resource not found"
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.status_code == 404
    
    def test_resource_not_found_custom_message(self):
        """Test ResourceNotFound accepts custom message."""
        # Act
        error = ResourceNotFound("User not found")
        
        # Assert
        assert error.message == "User not found"
    
    def test_resource_not_found_with_details(self):
        """Test ResourceNotFound accepts details."""
        # Arrange
        details = {"resource_type": "User", "id": "123"}
        
        # Act
        error = ResourceNotFound("User not found", details=details)
        
        # Assert
        assert error.details == details


class TestBadRequest:
    """Tests for BadRequest exception."""
    
    def test_bad_request_default_message(self):
        """Test BadRequest has correct default message."""
        # Act
        error = BadRequest()
        
        # Assert
        assert error.message == "Bad request"
        assert error.code == "BAD_REQUEST"
        assert error.status_code == 400
    
    def test_bad_request_custom_message(self):
        """Test BadRequest accepts custom message."""
        # Act
        error = BadRequest("Invalid email format")
        
        # Assert
        assert error.message == "Invalid email format"


class TestUnauthorized:
    """Tests for Unauthorized exception."""
    
    def test_unauthorized_default_message(self):
        """Test Unauthorized has correct default message."""
        # Act
        error = Unauthorized()
        
        # Assert
        assert error.message == "Unauthorized"
        assert error.code == "UNAUTHORIZED"
        assert error.status_code == 401
    
    def test_unauthorized_custom_message(self):
        """Test Unauthorized accepts custom message."""
        # Act
        error = Unauthorized("Token expired")
        
        # Assert
        assert error.message == "Token expired"


class TestForbidden:
    """Tests for Forbidden exception."""
    
    def test_forbidden_default_message(self):
        """Test Forbidden has correct default message."""
        # Act
        error = Forbidden()
        
        # Assert
        assert error.message == "Forbidden"
        assert error.code == "FORBIDDEN"
        assert error.status_code == 403
    
    def test_forbidden_custom_message(self):
        """Test Forbidden accepts custom message."""
        # Act
        error = Forbidden("Admin access required")
        
        # Assert
        assert error.message == "Admin access required"


class TestConflict:
    """Tests for Conflict exception."""
    
    def test_conflict_default_message(self):
        """Test Conflict has correct default message."""
        # Act
        error = Conflict()
        
        # Assert
        assert error.message == "Conflict"
        assert error.code == "CONFLICT"
        assert error.status_code == 409
    
    def test_conflict_custom_message(self):
        """Test Conflict accepts custom message."""
        # Act
        error = Conflict("Email already exists")
        
        # Assert
        assert error.message == "Email already exists"
    
    def test_conflict_with_details(self):
        """Test Conflict with details for duplicate resource."""
        # Arrange
        details = {"field": "email", "value": "test@example.com"}
        
        # Act
        error = Conflict("Duplicate entry", details=details)
        
        # Assert
        assert error.details["field"] == "email"


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""
    
    def test_all_exceptions_inherit_from_app_error(self):
        """Test all custom exceptions inherit from AppError."""
        # Assert
        assert issubclass(ResourceNotFound, AppError)
        assert issubclass(BadRequest, AppError)
        assert issubclass(Unauthorized, AppError)
        assert issubclass(Forbidden, AppError)
        assert issubclass(Conflict, AppError)
    
    def test_exceptions_can_be_caught_as_app_error(self):
        """Test all exceptions can be caught as AppError."""
        exceptions = [
            ResourceNotFound(),
            BadRequest(),
            Unauthorized(),
            Forbidden(),
            Conflict(),
        ]
        
        for exc in exceptions:
            try:
                raise exc
            except AppError as caught:
                assert caught.message is not None
                assert caught.code is not None
                assert caught.status_code >= 400
