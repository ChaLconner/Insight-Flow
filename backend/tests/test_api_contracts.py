"""
API Contract Tests.
Validates that API responses match expected schemas.
Ensures API contracts are not accidentally broken.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Any
from datetime import datetime
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Response Schema Definitions
# =============================================================================

class HealthResponse(BaseModel):
    """Expected schema for /health endpoint."""
    status: str
    environment: str
    version: str


class FullHealthResponse(BaseModel):
    """Expected schema for /health/full endpoint."""
    status: str
    timestamp: float
    environment: str
    version: str
    components: dict


class UserResponse(BaseModel):
    """Expected schema for user data."""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    avatar: Optional[str] = None
    created_at: Optional[str] = None


class LoginResponse(BaseModel):
    """Expected schema for login response."""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool


class ErrorResponse(BaseModel):
    """Expected schema for error responses."""
    detail: str


class ProjectResponse(BaseModel):
    """Expected schema for project data."""
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    owner_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskResponse(BaseModel):
    """Expected schema for task data."""
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    project_id: str
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None
    created_at: Optional[str] = None


class DashboardStatsResponse(BaseModel):
    """Expected schema for dashboard statistics."""
    total_projects: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int


# =============================================================================
# Contract Test Helpers
# =============================================================================

def validate_response_schema(response_data: dict, schema_class: type) -> tuple:
    """
    Validate response data against a Pydantic schema.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        schema_class(**response_data)
        return True, None
    except ValidationError as e:
        return False, str(e)


def validate_list_response(response_data: list, item_schema: type) -> tuple:
    """
    Validate a list response where each item should match a schema.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(response_data, list):
        return False, f"Expected list, got {type(response_data)}"
    
    for i, item in enumerate(response_data):
        try:
            item_schema(**item)
        except ValidationError as e:
            return False, f"Item {i} validation failed: {e}"
    
    return True, None


# =============================================================================
# Contract Tests
# =============================================================================

class TestHealthContractTests:
    """Contract tests for health endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_response_schema(self):
        """Test /health response matches expected schema."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            
            is_valid, error = validate_response_schema(
                response.json(), HealthResponse
            )
            assert is_valid, f"Schema validation failed: {error}"
    
    @pytest.mark.asyncio
    async def test_full_health_response_schema(self):
        """Test /health/full response matches expected schema."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health/full")
            
            assert response.status_code == 200
            
            data = response.json()
            
            # Validate required fields
            assert "status" in data
            assert "timestamp" in data
            assert "components" in data
            
            # Validate component structure
            components = data["components"]
            assert isinstance(components, dict)


class TestAuthContractTests:
    """Contract tests for authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_error_response_schema(self):
        """Test login error response matches expected schema."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "wrongpassword"
                }
            )
            
            # Should return error (401, 404, or 500)
            assert response.status_code in [400, 401, 404, 500]
            
            data = response.json()
            # Error response should have detail field
            assert "detail" in data or "message" in data
    
    @pytest.mark.asyncio
    async def test_register_validation_error_schema(self):
        """Test registration validation error response."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            # Send invalid data (missing required fields)
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "invalid-email",  # Invalid email format
                }
            )
            
            # Should return validation error or bad request
            assert response.status_code in [400, 422]
            
            data = response.json()
            # Error response should have detail field
            assert "detail" in data or "message" in data


class TestProjectContractTests:
    """Contract tests for project endpoints."""
    
    @pytest.mark.asyncio
    async def test_projects_unauthorized_schema(self):
        """Test projects endpoint returns proper error when unauthorized."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/api/v1/projects")
            
            # Should require authentication
            assert response.status_code in [400, 401, 403]
            
            data = response.json()
            # Error response should have detail field
            assert "detail" in data or "message" in data


class TestMetricsContractTests:
    """Contract tests for metrics endpoint."""
    
    @pytest.mark.asyncio
    async def test_metrics_format(self):
        """Test /metrics returns Prometheus format."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/metrics")
            
            assert response.status_code == 200
            assert "text/plain" in response.headers.get("content-type", "")
            
            content = response.text
            
            # Prometheus format should have HELP and TYPE comments
            # or metric names
            assert len(content) > 0
            
            # Check for expected metric patterns
            lines = content.split("\n")
            has_metrics = any(
                line.startswith("#") or 
                any(metric in line for metric in ["db_pool", "cache", "process"])
                for line in lines
            )
            assert has_metrics, "No valid Prometheus metrics found"


class TestErrorContractTests:
    """Contract tests for error responses."""
    
    @pytest.mark.asyncio
    async def test_404_error_schema(self):
        """Test 404 error response schema."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/nonexistent-endpoint-12345")
            
            assert response.status_code in [404, 400]
            assert "application/json" in response.headers.get("content-type", "")
            
            data = response.json()
            # Error response should have detail field
            assert "detail" in data or "message" in data
    
    @pytest.mark.asyncio
    async def test_method_not_allowed_schema(self):
        """Test 405 error response schema."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            # POST to a GET-only endpoint
            response = await client.post("/health", json={})
            
            # Should return method not allowed or similar
            assert response.status_code in [405, 422]


class TestResponseHeadersContract:
    """Contract tests for response headers."""
    
    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """Test that all required security headers are present."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            headers = response.headers
            
            # Required security headers
            required_headers = [
                "x-frame-options",
                "x-content-type-options",
                "x-xss-protection",
                "content-security-policy",
            ]
            
            for header in required_headers:
                assert header in headers, f"Missing security header: {header}"
    
    @pytest.mark.asyncio
    async def test_request_id_header(self):
        """Test that X-Request-ID header is present."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            assert "x-request-id" in response.headers
            
            # Request ID should be a valid format
            request_id = response.headers["x-request-id"]
            assert len(request_id) > 0
    
    @pytest.mark.asyncio
    async def test_content_type_json(self):
        """Test that API responses have correct content type."""
        from main import app
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            response = await client.get("/health")
            
            assert "application/json" in response.headers.get("content-type", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
