"""Tests for active and compatibility analytics API endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from async_dependencies import require_project_member
from database import get_async_db
from dependencies.services import get_project_service, get_task_history_service
from main import app
from routers.auth import get_current_active_user

client = TestClient(app)


def mock_get_current_active_user():
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.role = "user"
    return mock_user


def test_analytics_endpoint_requires_auth():
    """Test that analytics endpoints require authentication."""
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_project_recent_activity_compat_endpoint(monkeypatch):
    project_id = uuid.uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.name = "Test Project"

    mock_session = AsyncMock()
    mock_user_result = MagicMock()
    mock_user_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_user_result)

    mock_history_service = AsyncMock()
    activity = MagicMock()
    activity.id = uuid.uuid4()
    activity.user_id = uuid.uuid4()
    activity.activity_type.value = "task_created"
    activity.timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    activity.project_id = project_id
    activity.task_title = "Test Task"
    activity.description = "Created task"
    activity.new_values = None
    mock_history_service.get_recent_activities.return_value = [activity]

    async def override_require_project_member():
        return mock_project

    monkeypatch.setitem(
        app.dependency_overrides, get_current_active_user, mock_get_current_active_user
    )
    monkeypatch.setitem(
        app.dependency_overrides, require_project_member, override_require_project_member
    )
    monkeypatch.setitem(app.dependency_overrides, get_async_db, lambda: mock_session)
    monkeypatch.setitem(
        app.dependency_overrides, get_task_history_service, lambda: mock_history_service
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:
            response = await ac.get(f"/api/v1/analytics/projects/{project_id}/activity")

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total_count"] == 1
        assert data["activities"][0]["project_id"] == str(project_id)
    finally:
        monkeypatch.setattr(app, "dependency_overrides", {})


@pytest.mark.asyncio
async def test_batch_recent_activity_compat_endpoint(monkeypatch):
    project_id = uuid.uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.name = "Test Project"

    current_user = mock_get_current_active_user()
    mock_session = AsyncMock()
    mock_user_result = MagicMock()
    mock_user_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_user_result)

    mock_project_service = AsyncMock()
    mock_project_service.get_projects.return_value = [mock_project]

    mock_history_service = AsyncMock()
    activity = MagicMock()
    activity.id = uuid.uuid4()
    activity.user_id = uuid.uuid4()
    activity.activity_type.value = "task_created"
    activity.timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    activity.project_id = project_id
    activity.task_title = "Test Task"
    activity.description = "Created task"
    activity.new_values = None
    mock_history_service.get_recent_activities_for_projects.return_value = [activity]

    monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: current_user)
    monkeypatch.setitem(app.dependency_overrides, get_async_db, lambda: mock_session)
    monkeypatch.setitem(app.dependency_overrides, get_project_service, lambda: mock_project_service)
    monkeypatch.setitem(
        app.dependency_overrides, get_task_history_service, lambda: mock_history_service
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:
            response = await ac.post(
                "/api/v1/analytics/activity/batch",
                json={"project_ids": [str(project_id)], "limit": 5},
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data[0]["projectId"] == str(project_id)
        assert data[0]["activities"][0]["project_id"] == str(project_id)
    finally:
        monkeypatch.setattr(app, "dependency_overrides", {})
