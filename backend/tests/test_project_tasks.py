"""
Tests for routers/project_tasks.py

Tests for project task endpoints authentication.
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from main import app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def unauthenticated_client():
    """Test client without authentication."""
    with TestClient(app) as client:
        yield client


# ============================================================================
# Tests for Project Tasks Authentication
# ============================================================================

class TestProjectTasksAuthentication:
    def test_get_project_tasks_requires_auth(self, unauthenticated_client):
        """Test getting project tasks requires authentication."""
        project_id = uuid4()
        response = unauthenticated_client.get(f"/api/v1/projects/{project_id}/tasks")
        assert response.status_code == 401
    
    def test_create_project_task_requires_auth(self, unauthenticated_client):
        """Test creating project task requires authentication."""
        project_id = uuid4()
        response = unauthenticated_client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={"title": "Test Task", "type": "feature"}
        )
        assert response.status_code == 401
    
    def test_get_project_task_requires_auth(self, unauthenticated_client):
        """Test getting single project task requires authentication."""
        project_id = uuid4()
        task_id = uuid4()
        response = unauthenticated_client.get(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        assert response.status_code == 401
    
    def test_update_project_task_requires_auth(self, unauthenticated_client):
        """Test updating project task requires authentication."""
        project_id = uuid4()
        task_id = uuid4()
        response = unauthenticated_client.put(
            f"/api/v1/projects/{project_id}/tasks/{task_id}",
            json={"title": "Updated Task"}
        )
        assert response.status_code == 401
    
    def test_delete_project_task_requires_auth(self, unauthenticated_client):
        """Test deleting project task requires authentication."""
        project_id = uuid4()
        task_id = uuid4()
        response = unauthenticated_client.delete(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        assert response.status_code == 401
    
    def test_update_task_status_requires_auth(self, unauthenticated_client):
        """Test updating task status requires authentication."""
        project_id = uuid4()
        task_id = uuid4()
        response = unauthenticated_client.put(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/status",
            json={"status": "done"}
        )
        assert response.status_code == 401
