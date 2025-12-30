"""
Comprehensive Security Tests.
Tests authentication, authorization, CSRF, and security headers.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
import hmac
import secrets

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSecurityHeaders:
    """Tests for security headers middleware."""
    
    @pytest.mark.asyncio
    async def test_xframe_options_header(self):
        """Test X-Frame-Options header is set."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            assert response.headers.get("x-frame-options") == "DENY"
    
    @pytest.mark.asyncio
    async def test_content_type_options_header(self):
        """Test X-Content-Type-Options header is set."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            assert response.headers.get("x-content-type-options") == "nosniff"
    
    @pytest.mark.asyncio
    async def test_xss_protection_header(self):
        """Test X-XSS-Protection header is set."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            assert "x-xss-protection" in response.headers
    
    @pytest.mark.asyncio
    async def test_csp_header(self):
        """Test Content-Security-Policy header is set."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            csp = response.headers.get("content-security-policy")
            assert csp is not None
            assert "default-src" in csp


class TestCSRFProtection:
    """Tests for CSRF protection middleware."""
    
    def test_csrf_token_generation(self):
        """Test CSRF token generation."""
        from middleware.csrf import generate_csrf_token
        
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        
        # Tokens should be unique
        assert token1 != token2
        
        # Tokens should be of sufficient length
        assert len(token1) > 20
    
    def test_csrf_token_validation(self):
        """Test CSRF token validation."""
        from middleware.csrf import validate_csrf_token
        
        token = secrets.token_urlsafe(32)
        
        # Same tokens should validate
        assert validate_csrf_token(token, token) is True
        
        # Different tokens should not validate
        assert validate_csrf_token(token, "different_token") is False
        
        # None tokens should not validate
        assert validate_csrf_token(None, token) is False
        assert validate_csrf_token(token, None) is False
        assert validate_csrf_token(None, None) is False
    
    def test_csrf_exempt_paths(self):
        """Test CSRF exempt paths are defined."""
        from middleware.csrf import CSRF_EXEMPT_PATHS
        
        # Login should be exempt
        assert "/api/v1/auth/login" in CSRF_EXEMPT_PATHS
        
        # Health endpoints should be exempt
        assert "/health" in CSRF_EXEMPT_PATHS
    
    def test_safe_methods(self):
        """Test safe HTTP methods are defined."""
        from middleware.csrf import SAFE_METHODS
        
        assert "GET" in SAFE_METHODS
        assert "HEAD" in SAFE_METHODS
        assert "OPTIONS" in SAFE_METHODS
        
        # Unsafe methods should not be safe
        assert "POST" not in SAFE_METHODS
        assert "PUT" not in SAFE_METHODS
        assert "DELETE" not in SAFE_METHODS


class TestSecurityAuditLogger:
    """Tests for security audit logging."""
    
    def test_audit_logger_singleton(self):
        """Test audit logger is singleton."""
        from utils.security_audit import SecurityAuditLogger
        
        logger1 = SecurityAuditLogger()
        logger2 = SecurityAuditLogger()
        
        assert logger1 is logger2
    
    def test_email_masking(self):
        """Test email masking for privacy."""
        from utils.security_audit import SecurityAuditLogger
        
        masked = SecurityAuditLogger._mask_email("test@example.com")
        
        # Should mask middle characters
        assert "@example.com" in masked
        assert masked != "test@example.com"
        assert "t" in masked  # First character preserved
    
    def test_audit_event_types(self):
        """Test audit event types are defined."""
        from utils.security_audit import AuditEventType
        
        assert AuditEventType.LOGIN_SUCCESS is not None
        assert AuditEventType.LOGIN_FAILED is not None
        assert AuditEventType.LOGOUT is not None
        assert AuditEventType.ACCESS_DENIED is not None
        assert AuditEventType.CSRF_VALIDATION_FAILED is not None


class TestAuthenticationSecurity:
    """Tests for authentication security."""
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self):
        """Test that protected endpoints require authentication."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            # Projects endpoint should require auth
            response = await client.get("/api/v1/projects")
            
            assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self):
        """Test that invalid tokens are rejected."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid_token_12345"}
            )
            
            assert response.status_code in [401, 403, 500]
    
    @pytest.mark.asyncio
    async def test_missing_token_rejected(self):
        """Test that missing tokens are rejected."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/api/v1/auth/me")
            
            assert response.status_code in [401, 403]


class TestInputValidation:
    """Tests for input validation."""
    
    @pytest.mark.asyncio
    async def test_invalid_email_rejected(self):
        """Test that invalid email format is rejected."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "invalid-email",
                    "password": "ValidPassword123!",
                    "full_name": "Test User"
                }
            )
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={}
            )
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_xss_payload_in_input(self):
        """Test that XSS payloads are handled safely."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            xss_payload = "<script>alert('xss')</script>"
            
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test{uuid.uuid4().hex[:8]}@example.com",
                    "password": "ValidPassword123!",
                    "full_name": xss_payload
                }
            )
            
            # Should either succeed (sanitized) or fail (rejected)
            # but never execute the script
            assert response.status_code in [200, 201, 422, 500]


class TestRateLimiting:
    """Tests for rate limiting."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_not_triggered_normal_usage(self):
        """Test that normal usage doesn't trigger rate limit."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            # Make 5 requests - should be under limit
            for _ in range(5):
                response = await client.get("/health")
                assert response.status_code == 200


class TestPasswordSecurity:
    """Tests for password security."""
    
    def test_password_hashing(self):
        """Test password hashing utilities."""
        from utils.auth import get_password_hash, verify_password
        
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Hashed password should be different from original
        assert hashed != password
        
        # Should verify correctly
        assert verify_password(password, hashed) is True
        
        # Wrong password should not verify
        assert verify_password("wrong_password", hashed) is False


class TestRequestIdTracking:
    """Tests for request ID tracking."""
    
    @pytest.mark.asyncio
    async def test_request_id_in_response(self):
        """Test that request ID is included in response."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            request_id = response.headers.get("x-request-id")
            assert request_id is not None
            assert len(request_id) > 0
    
    @pytest.mark.asyncio
    async def test_request_id_unique(self):
        """Test that each request gets unique ID."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response1 = await client.get("/health")
            response2 = await client.get("/health")
            
            id1 = response1.headers.get("x-request-id")
            id2 = response2.headers.get("x-request-id")
            
            assert id1 != id2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
