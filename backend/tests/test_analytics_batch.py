"""
Tests for analytics batch API endpoints.
Updated to work with async services.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from database import get_async_db
from main import app
from routers.auth import get_current_active_user

client = TestClient(app)


def mock_get_current_active_user():
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.role = "user"
    return mock_user


@pytest.mark.asyncio
async def test_get_batch_recent_activity():
    """
    Test batch recent activity endpoint.
    """
    from httpx import ASGITransport, AsyncClient

    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    # Mock DB session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalar.return_value = 0
    mock_session.execute = AsyncMock(return_value=mock_result)
    app.dependency_overrides[get_async_db] = lambda: mock_session

    try:
        with (
            patch("services.async_task_history_service.AsyncTaskHistoryService") as MockTaskService,
            patch("services.async_project_service.AsyncProjectService") as MockProjService,
        ):
            # Setup Task Service Mock
            mock_task_service = MockTaskService.return_value
            activity = MagicMock()
            activity.user_id = uuid.uuid4()
            activity.activity_type.value = "task_created"
            activity.timestamp.isoformat.return_value = "2023-01-01T00:00:00"
            activity.project_id = uuid.uuid4()
            activity.task_title = "Test Task"
            activity.description = "Test Description"
            mock_task_service.get_batch_recent_activities = AsyncMock(return_value=[activity])
            mock_task_service.get_recent_activities_for_projects = AsyncMock(
                return_value=[activity]
            )

            # Setup Project Service Mock
            mock_proj_service = MockProjService.return_value
            project = MagicMock()
            project.id = activity.project_id
            project.name = "Test Project"
            mock_proj_service.get_projects = AsyncMock(return_value=[project])

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as ac:
                response = await ac.post(
                    "/api/v1/analytics/activity/batch",
                    json={"project_ids": [str(activity.project_id)], "limit": 5},
                )

            # Use assertion message for debugging instead of print
            assert response.status_code == 200, f"Error Response: {response.text}"
            data = response.json()
            assert len(data) == 1
            assert data[0]["projectId"] == str(activity.project_id)
    finally:
        app.dependency_overrides = {}


def test_analytics_batch_endpoint_requires_auth():
    """Test that analytics batch endpoint requires authentication."""
    response = client.post(
        "/api/v1/analytics/activity/batch", json={"project_ids": [str(uuid.uuid4())], "limit": 5}
    )
    assert response.status_code == 401


def test_analytics_batch_endpoint_validates_input():
    """Test that analytics batch endpoint validates input."""
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

    # Missing project_ids should fail validation
    response = client.post("/api/v1/analytics/activity/batch", json={"limit": 5})
    # Should return 422 for validation error
    assert response.status_code == 422

    app.dependency_overrides = {}
