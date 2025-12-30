"""
Tests for analytics API endpoints.
Updated to work with async services.
"""
from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import uuid
from routers.auth import get_current_active_user
from database import get_async_db

client = TestClient(app)


def mock_get_current_active_user():
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.role = "user"
    return mock_user


@pytest.mark.asyncio
async def test_get_recent_activity_optimized():
    """
    Test recent activity endpoint with optimized async service.
    """
    from httpx import AsyncClient, ASGITransport
    from async_dependencies import require_project_member
    
    project_id = str(uuid.uuid4())
    mock_project = MagicMock()
    mock_project.id = uuid.UUID(project_id)
    mock_project.name = "Test Project"
    
    async def mock_permission(project_id: str):
        return mock_project
    
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[require_project_member] = mock_permission
    
    # Mock async session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalar.return_value = 0
    mock_session.execute = AsyncMock(return_value=mock_result)
    app.dependency_overrides[get_async_db] = lambda: mock_session
    
    try:
        with patch('services.async_task_history_service.AsyncTaskHistoryService') as MockService:
            mock_service = MockService.return_value
            
            # Mock async activities
            activity1 = MagicMock()
            activity1.user_id = uuid.uuid4()
            activity1.activity_type.value = "task_created"
            activity1.timestamp.isoformat.return_value = "2023-01-01T00:00:00"
            activity1.project_id = mock_project.id
            
            activity2 = MagicMock()
            activity2.user_id = uuid.uuid4()
            activity2.activity_type.value = "task_updated"
            activity2.timestamp.isoformat.return_value = "2023-01-02T00:00:00"
            activity2.project_id = mock_project.id

            mock_service.get_recent_activities = AsyncMock(return_value=[activity1, activity2])
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
                response = await ac.get(f"/api/v1/analytics/projects/{project_id}/activity")
                
            if response.status_code != 200:
                print(f"Error Response: {response.text}")
                
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
    finally:
        app.dependency_overrides = {}


def test_analytics_endpoint_requires_auth():
    """Test that analytics endpoints require authentication."""
    # Test global overview endpoint
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 401
