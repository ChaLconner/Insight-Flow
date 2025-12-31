"""
Tests for routers/dashboard.py endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from main import app
from dependencies.services import get_dashboard_service
from routers.auth import get_current_active_user
from models.user import User


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_dashboard_service():
    """Mock AsyncDashboardService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_current_user():
    """Mock User model."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.role = "user"
    user.is_active = True
    return user


@pytest.fixture
def client(mock_dashboard_service, mock_current_user):
    """Test client with mocks."""
    app.dependency_overrides[get_dashboard_service] = lambda: mock_dashboard_service
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_user
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides = {}


# ============================================================================
# Tests for Dashboard Overview
# ============================================================================

def test_get_dashboard_overview_success(client, mock_dashboard_service, mock_current_user):
    """Test getting dashboard overview."""
    mock_dashboard_service.get_overview_stats.return_value = {
        "total_projects": 5,
        "total_tasks": 20,
        "completed_tasks": 15,
        "overdue_tasks": 2,
        "upcoming_deadlines": 3
    }
    mock_dashboard_service.get_recent_projects.return_value = [
        {
            "id": str(uuid4()),
            "name": "Project 1",
            "description": "Description",
            "task_count": 10,
            "completed_tasks": 5,
            "progress": 50,
            "updated_at": datetime.now().isoformat()
        }
    ]
    mock_dashboard_service.get_recent_activities.return_value = [
        {
            "id": str(uuid4()),
            "user": {"id": str(uuid4()), "name": "Test User", "avatar": None},
            "action": "created task",
            "target": "Task 1",
            "time": datetime.now().isoformat(),
            "project": {"id": str(uuid4()), "name": "Project 1"}
        }
    ]
    
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    assert "recentProjects" in data
    assert "recentActivities" in data


def test_get_dashboard_overview_error(client, mock_dashboard_service):
    """Test dashboard overview error handling."""
    mock_dashboard_service.get_overview_stats.side_effect = Exception("Database error")
    
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 500


# ============================================================================
# Tests for Today Tasks
# ============================================================================

def test_get_today_tasks_success(client, mock_dashboard_service):
    """Test getting today's tasks."""
    mock_dashboard_service.get_today_tasks.return_value = [
        {"id": str(uuid4()), "title": "Task 1", "status": "pending"},
        {"id": str(uuid4()), "title": "Task 2", "status": "in_progress"}
    ]
    
    response = client.get("/api/v1/dashboard/today-tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_today_tasks_error(client, mock_dashboard_service):
    """Test today tasks error handling."""
    mock_dashboard_service.get_today_tasks.side_effect = Exception("Error")
    
    response = client.get("/api/v1/dashboard/today-tasks")
    assert response.status_code == 500


# ============================================================================
# Tests for Recent Projects
# ============================================================================

def test_get_recent_projects_success(client, mock_dashboard_service):
    """Test getting recent projects."""
    mock_dashboard_service.get_recent_projects.return_value = [
        {"id": str(uuid4()), "name": "Project 1"},
        {"id": str(uuid4()), "name": "Project 2"}
    ]
    
    response = client.get("/api/v1/dashboard/recent-projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_recent_projects_error(client, mock_dashboard_service):
    """Test recent projects error handling."""
    mock_dashboard_service.get_recent_projects.side_effect = Exception("Error")
    
    response = client.get("/api/v1/dashboard/recent-projects")
    assert response.status_code == 500


# ============================================================================
# Tests for Team Activity
# ============================================================================

def test_get_team_activity_success(client, mock_dashboard_service):
    """Test getting team activity."""
    mock_dashboard_service.get_recent_activities.return_value = [
        {"id": str(uuid4()), "action": "created", "user": {"name": "User1"}}
    ]
    
    response = client.get("/api/v1/dashboard/team-activity")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_team_activity_error(client, mock_dashboard_service):
    """Test team activity error handling."""
    mock_dashboard_service.get_recent_activities.side_effect = Exception("Error")
    
    response = client.get("/api/v1/dashboard/team-activity")
    assert response.status_code == 500
