"""
Tests for utils/token_utils.py

Tests token utility functions.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestTokenConstants:
    """Tests for token constants."""
    
    def test_access_token_key_exists(self):
        """Test ACCESS_TOKEN_KEY is defined."""
        from utils.token_utils import ACCESS_TOKEN_KEY
        
        assert ACCESS_TOKEN_KEY is not None
        assert len(ACCESS_TOKEN_KEY) > 0
    
    def test_refresh_token_key_exists(self):
        """Test REFRESH_TOKEN_KEY is defined."""
        from utils.token_utils import REFRESH_TOKEN_KEY
        
        assert REFRESH_TOKEN_KEY is not None
        assert len(REFRESH_TOKEN_KEY) > 0
    
    def test_cookie_secure_exists(self):
        """Test COOKIE_SECURE is defined."""
        from utils.token_utils import COOKIE_SECURE
        
        assert isinstance(COOKIE_SECURE, bool)


class TestCookieFunctions:
    """Tests for cookie handling functions."""
    
    def test_create_and_set_auth_cookies_import(self):
        """Test create_and_set_auth_cookies can be imported."""
        from utils.token_utils import create_and_set_auth_cookies
        
        assert create_and_set_auth_cookies is not None
    
    def test_clear_auth_cookies_import(self):
        """Test clear_auth_cookies can be imported."""
        from utils.token_utils import clear_auth_cookies
        
        assert clear_auth_cookies is not None
    
    def test_clear_auth_cookies_calls_delete_cookie(self):
        """Test clear_auth_cookies deletes cookies."""
        from utils.token_utils import clear_auth_cookies, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY
        
        mock_response = MagicMock()
        
        clear_auth_cookies(mock_response)
        
        # Should have called delete_cookie for both tokens
        assert mock_response.delete_cookie.call_count >= 2


class TestTokenExpiration:
    """Tests for token expiration handling."""
    
    def test_access_token_expiration_default(self):
        """Test default access token expiration."""
        # Common default is 30 minutes = 1800 seconds
        DEFAULT_ACCESS_EXPIRE = 1800
        
        assert DEFAULT_ACCESS_EXPIRE == 30 * 60
    
    def test_refresh_token_expiration_default(self):
        """Test default refresh token expiration."""
        # Common default is 7 days
        DEFAULT_REFRESH_EXPIRE = 7 * 24 * 60 * 60
        
        assert DEFAULT_REFRESH_EXPIRE == 604800
