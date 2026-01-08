"""
Tests for routers/favorites.py endpoints.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import get_async_db
from main import app
from models.user import User
from routers.auth import get_current_active_user

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock()
    return db


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
def client(mock_db, mock_current_user):
    """Test client with mocks."""

    async def override_get_async_db():
        yield mock_db

    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


# ============================================================================
# Tests for Get Favorite IDs
# ============================================================================


def test_get_favorite_project_ids_success(client, mock_db):
    """Test getting favorite project IDs."""
    project_id_1 = uuid4()
    project_id_2 = uuid4()

    # Mock the result
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(project_id_1,), (project_id_2,)]
    mock_db.execute.return_value = mock_result

    response = client.get("/api/v1/favorites")
    assert response.status_code == 200
    data = response.json()
    assert "projectIds" in data
    assert len(data["projectIds"]) == 2


def test_get_favorite_project_ids_error(client, mock_db):
    """Test error handling for get favorite IDs."""
    mock_db.execute.side_effect = Exception("Database error")

    response = client.get("/api/v1/favorites")
    assert response.status_code == 500


# ============================================================================
# Tests for Get Favorite Projects
# ============================================================================


def test_get_favorite_projects_success(client, mock_db):
    """Test getting favorite projects with details."""
    project_id = uuid4()
    fav_id = uuid4()

    # Create mock favorite with project
    mock_fav = MagicMock()
    mock_fav.id = fav_id
    mock_fav.project_id = project_id
    mock_fav.created_at = datetime.now()
    mock_fav.project = MagicMock()
    mock_fav.project.name = "Test Project"
    mock_fav.project.description = "Test Description"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_fav]
    mock_db.execute.return_value = mock_result

    response = client.get("/api/v1/favorites/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["projectName"] == "Test Project"


def test_get_favorite_projects_error(client, mock_db):
    """Test error handling for get favorite projects."""
    mock_db.execute.side_effect = Exception("Database error")

    response = client.get("/api/v1/favorites/projects")
    assert response.status_code == 500


# ============================================================================
# Tests for Toggle Favorite
# ============================================================================


def test_toggle_favorite_add_success(client, mock_db):
    """Test adding a project to favorites via toggle."""
    project_id = uuid4()

    # Mock project exists
    mock_project = MagicMock()
    mock_project.name = "Test Project"

    mock_project_result = MagicMock()
    mock_project_result.scalar_one_or_none.return_value = mock_project

    # Mock favorite doesn't exist
    mock_fav_result = MagicMock()
    mock_fav_result.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_project_result, mock_fav_result]

    response = client.post("/api/v1/favorites/toggle", json={"projectId": str(project_id)})
    assert response.status_code == 200
    data = response.json()
    assert data["isFavorite"] is True


def test_toggle_favorite_remove_success(client, mock_db):
    """Test removing a project from favorites via toggle."""
    project_id = uuid4()

    # Mock project exists
    mock_project = MagicMock()
    mock_project.name = "Test Project"

    mock_project_result = MagicMock()
    mock_project_result.scalar_one_or_none.return_value = mock_project

    # Mock favorite exists
    mock_fav = MagicMock()
    mock_fav_result = MagicMock()
    mock_fav_result.scalar_one_or_none.return_value = mock_fav

    mock_db.execute.side_effect = [mock_project_result, mock_fav_result]

    response = client.post("/api/v1/favorites/toggle", json={"projectId": str(project_id)})
    assert response.status_code == 200
    data = response.json()
    assert data["isFavorite"] is False


def test_toggle_favorite_invalid_id(client, mock_db):
    """Test toggle favorite with invalid project ID."""
    response = client.post("/api/v1/favorites/toggle", json={"projectId": "invalid-uuid"})
    assert response.status_code == 400


def test_toggle_favorite_project_not_found(client, mock_db):
    """Test toggle favorite when project doesn't exist."""
    project_id = uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    response = client.post("/api/v1/favorites/toggle", json={"projectId": str(project_id)})
    assert response.status_code == 404


# ============================================================================
# Tests for Remove Favorite
# ============================================================================


def test_remove_favorite_success(client, mock_db):
    """Test removing a favorite."""
    project_id = uuid4()

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.execute.return_value = mock_result

    response = client.delete(f"/api/v1/favorites/{project_id}")
    assert response.status_code == 204


def test_remove_favorite_not_found(client, mock_db):
    """Test removing non-existent favorite."""
    project_id = uuid4()

    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_db.execute.return_value = mock_result

    response = client.delete(f"/api/v1/favorites/{project_id}")
    assert response.status_code == 404


def test_remove_favorite_invalid_id(client, mock_db):
    """Test removing favorite with invalid ID."""
    response = client.delete("/api/v1/favorites/invalid-uuid")
    assert response.status_code == 400


# ============================================================================
# Tests for Add Favorite
# ============================================================================


def test_add_favorite_success(client, mock_db):
    """Test adding a favorite."""
    project_id = uuid4()

    # Mock project exists
    mock_project = MagicMock()
    mock_project.name = "Test Project"

    mock_project_result = MagicMock()
    mock_project_result.scalar_one_or_none.return_value = mock_project

    # Mock favorite doesn't exist
    mock_fav_result = MagicMock()
    mock_fav_result.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_project_result, mock_fav_result]

    response = client.post(f"/api/v1/favorites/{project_id}")
    assert response.status_code == 201
    data = response.json()
    assert data["isFavorite"] is True


def test_add_favorite_already_exists(client, mock_db):
    """Test adding a favorite that already exists."""
    project_id = uuid4()

    # Mock project exists
    mock_project = MagicMock()
    mock_project.name = "Test Project"

    mock_project_result = MagicMock()
    mock_project_result.scalar_one_or_none.return_value = mock_project

    # Mock favorite already exists
    mock_fav = MagicMock()
    mock_fav_result = MagicMock()
    mock_fav_result.scalar_one_or_none.return_value = mock_fav

    mock_db.execute.side_effect = [mock_project_result, mock_fav_result]

    response = client.post(f"/api/v1/favorites/{project_id}")
    assert response.status_code == 201  # Returns 201 with message that it already exists


def test_add_favorite_project_not_found(client, mock_db):
    """Test adding favorite when project doesn't exist."""
    project_id = uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    response = client.post(f"/api/v1/favorites/{project_id}")
    assert response.status_code == 404


def test_add_favorite_invalid_id(client, mock_db):
    """Test adding favorite with invalid ID."""
    response = client.post("/api/v1/favorites/invalid-uuid")
    assert response.status_code == 400
