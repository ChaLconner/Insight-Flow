"""
Comprehensive tests for utils/auth.py

Tests follow best practices:
- Test password hashing is secure (bcrypt)
- Test JWT token creation and verification
- Test error handling for invalid tokens
- No secrets in test code
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import timedelta
import time


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_get_password_hash_returns_hash(self):
        """Test password hashing returns a non-empty string."""
        from utils.auth import get_password_hash
        
        # Arrange
        password = "TestPassword123!"
        
        # Act
        hashed = get_password_hash(password)
        
        # Assert
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != password  # Hash should differ from original
    
    def test_password_hash_is_bcrypt(self):
        """Test password hash uses bcrypt format."""
        from utils.auth import get_password_hash
        
        # Act
        hashed = get_password_hash("password")
        
        # Assert - bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")
    
    def test_same_password_different_hashes(self):
        """Test same password produces different hashes (salt)."""
        from utils.auth import get_password_hash
        
        # Arrange
        password = "SamePassword"
        
        # Act
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Assert - should be different due to salt
        assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        from utils.auth import get_password_hash, verify_password
        
        # Arrange
        password = "CorrectPassword123"
        hashed = get_password_hash(password)
        
        # Act
        result = verify_password(password, hashed)
        
        # Assert
        assert result is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        from utils.auth import get_password_hash, verify_password
        
        # Arrange
        password = "CorrectPassword"
        hashed = get_password_hash(password)
        
        # Act
        result = verify_password("WrongPassword", hashed)
        
        # Assert
        assert result is False
    
    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        from utils.auth import get_password_hash, verify_password
        
        # Arrange
        hashed = get_password_hash("password")
        
        # Act
        result = verify_password("", hashed)
        
        # Assert
        assert result is False


class TestCreateAccessToken:
    """Tests for JWT token creation."""
    
    def test_create_access_token_returns_string(self):
        """Test token creation returns a string."""
        from utils.auth import create_access_token
        
        # Arrange
        data = {"sub": "user@example.com"}
        
        # Act
        token = create_access_token(data)
        
        # Assert
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_has_three_parts(self):
        """Test JWT token has correct structure (header.payload.signature)."""
        from utils.auth import create_access_token
        
        # Arrange
        data = {"sub": "test_user"}
        
        # Act
        token = create_access_token(data)
        parts = token.split(".")
        
        # Assert
        assert len(parts) == 3
    
    def test_create_access_token_with_custom_expiry(self):
        """Test token creation with custom expiry."""
        from utils.auth import create_access_token
        
        # Arrange
        data = {"sub": "user"}
        custom_expiry = timedelta(hours=2)
        
        # Act
        token = create_access_token(data, expires_delta=custom_expiry)
        
        # Assert
        assert token is not None
    
    def test_create_access_token_includes_jti(self):
        """Test token includes JWT ID (jti) for blacklisting."""
        from utils.auth import create_access_token, verify_token
        
        # Arrange
        data = {"sub": "user"}
        
        # Act
        token = create_access_token(data)
        payload = verify_token(token)
        
        # Assert
        assert "jti" in payload
        assert len(payload["jti"]) > 0


class TestVerifyToken:
    """Tests for JWT token verification."""
    
    def test_verify_valid_token(self):
        """Test verification of valid token."""
        from utils.auth import create_access_token, verify_token
        
        # Arrange
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        # Act
        payload = verify_token(token)
        
        # Assert
        assert payload["sub"] == "user@example.com"
        assert payload["user_id"] == "123"
    
    def test_verify_token_empty_raises_exception(self):
        """Test verification of empty token raises exception."""
        from utils.auth import verify_token
        from fastapi import HTTPException
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_token("")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_token_invalid_structure_raises_exception(self):
        """Test verification of malformed token raises exception."""
        from utils.auth import verify_token
        from fastapi import HTTPException
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_token("not.a.valid.token.format")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_token_invalid_signature_raises_exception(self):
        """Test verification of token with bad signature raises exception."""
        from utils.auth import verify_token
        from fastapi import HTTPException
        
        # Arrange - a token with invalid signature
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalidsignature"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_token(fake_token)
        
        assert exc_info.value.status_code == 401


class TestAuthenticateUser:
    """Tests for user authentication function."""
    
    def test_authenticate_user_returns_false_for_none(self):
        """Test authentication returns False when user is None."""
        from utils.auth import authenticate_user
        
        # Act
        result = authenticate_user(None, "password")
        
        # Assert
        assert result is False
    
    def test_authenticate_user_returns_false_for_no_hash(self):
        """Test authentication returns False when user has no hashed_password."""
        from utils.auth import authenticate_user
        
        # Arrange
        user = MagicMock()
        user.hashed_password = None
        
        # Act
        result = authenticate_user(user, "password")
        
        # Assert
        assert result is False
    
    def test_authenticate_user_correct_password(self):
        """Test authentication with correct password."""
        from utils.auth import authenticate_user, get_password_hash
        
        # Arrange
        password = "CorrectPassword123"
        user = MagicMock()
        user.hashed_password = get_password_hash(password)
        
        # Act
        result = authenticate_user(user, password)
        
        # Assert
        assert result is True
    
    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password."""
        from utils.auth import authenticate_user, get_password_hash
        
        # Arrange
        user = MagicMock()
        user.hashed_password = get_password_hash("CorrectPassword")
        
        # Act
        result = authenticate_user(user, "WrongPassword")
        
        # Assert
        assert result is False


class TestGetTokenExpiration:
    """Tests for token expiration extraction."""
    
    def test_get_expiration_from_valid_token(self):
        """Test extracting expiration from valid token."""
        from utils.auth import create_access_token, get_token_expiration
        
        # Arrange
        data = {"sub": "user"}
        token = create_access_token(data, expires_delta=timedelta(hours=1))
        
        # Act
        expiration = get_token_expiration(token)
        
        # Assert
        assert expiration is not None
    
    def test_get_expiration_from_invalid_token(self):
        """Test extracting expiration from invalid token returns None."""
        from utils.auth import get_token_expiration
        
        # Act
        result = get_token_expiration("invalid.token")
        
        # Assert
        assert result is None
    
    def test_get_expiration_from_empty_token(self):
        """Test extracting expiration from empty token returns None."""
        from utils.auth import get_token_expiration
        
        # Act
        result = get_token_expiration("")
        
        # Assert
        assert result is None
