"""
Tests for routers/tasks.py

Tests for tasks router authentication.
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
# Tests for Tasks Router Authentication
# ============================================================================

class TestTasksAuthentication:
    def test_my_tasks_requires_auth(self, unauthenticated_client):
        """Test my-tasks endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/tasks/my-tasks")
        assert response.status_code == 401
    
    def test_task_stats_requires_auth(self, unauthenticated_client):
        """Test task stats endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/tasks/stats")
        assert response.status_code == 401
    
    def test_due_soon_requires_auth(self, unauthenticated_client):
        """Test due-soon endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/tasks/due-soon")
        assert response.status_code == 401
    
    def test_overdue_requires_auth(self, unauthenticated_client):
        """Test overdue endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/tasks/overdue")
        assert response.status_code == 401
    
    def test_get_single_task_requires_auth(self, unauthenticated_client):
        """Test getting single task requires authentication."""
        task_id = uuid4()
        response = unauthenticated_client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 401
    
    def test_update_task_requires_auth(self, unauthenticated_client):
        """Test updating task requires authentication."""
        task_id = uuid4()
        response = unauthenticated_client.put(
            f"/api/v1/tasks/{task_id}",
            json={"title": "Updated Task"}
        )
        assert response.status_code == 401
    
    def test_delete_task_requires_auth(self, unauthenticated_client):
        """Test deleting task requires authentication."""
        task_id = uuid4()
        response = unauthenticated_client.delete(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 401
