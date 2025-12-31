"""
Tests for utils/validators.py
"""

import pytest
from uuid import uuid4, UUID
from fastapi import HTTPException

from utils.validators import validate_uuid, validate_email, validate_password_strength


class TestValidateUuid:
    def test_validate_uuid_valid_string(self):
        """Test validating a valid UUID string."""
        valid_uuid = str(uuid4())
        result = validate_uuid(valid_uuid)
        assert isinstance(result, UUID)
        assert str(result) == valid_uuid

    def test_validate_uuid_invalid_string(self):
        """Test validating an invalid UUID string."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("not-a-valid-uuid")
        assert exc_info.value.status_code == 422

    def test_validate_uuid_empty_string(self):
        """Test validating an empty string."""
        with pytest.raises(HTTPException):
            validate_uuid("")

    def test_validate_uuid_custom_message(self):
        """Test custom error message."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("invalid", "Custom error message")
        assert "Custom error message" in str(exc_info.value.detail)


class TestValidateEmail:
    def test_validate_email_valid(self):
        """Test validating a valid email."""
        email = "test@example.com"
        result = validate_email(email)
        assert result == email

    def test_validate_email_invalid(self):
        """Test validating an invalid email."""
        with pytest.raises(HTTPException) as exc_info:
            validate_email("invalid-email")
        assert exc_info.value.status_code == 422

    def test_validate_email_missing_domain(self):
        """Test email without domain."""
        with pytest.raises(HTTPException):
            validate_email("test@")


class TestValidatePasswordStrength:
    def test_validate_password_valid(self):
        """Test validating a valid password."""
        password = "StrongPass123"
        result = validate_password_strength(password)
        assert result == password

    def test_validate_password_too_short(self):
        """Test password too short."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password_strength("short")
        assert exc_info.value.status_code == 422
        assert "8 characters" in str(exc_info.value.detail)
