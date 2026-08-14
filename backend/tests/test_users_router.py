from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import get_async_db
from dependencies.services import get_notification_service, get_user_service
from main import app
from models.user import User
from routers.auth import get_current_active_user

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_user_service():
    """Mock UserService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_current_user():
    """Mock User model."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    user.first_name = None
    user.last_name = None
    user.username = "testuser"
    user.phone = None
    user.bio = None
    user.location = None
    user.website = None
    user.role = "admin"
    user.is_active = True
    user.avatar_url = "/static/uploads/old.png"
    return user


@pytest.fixture
def mock_notification_service():
    service = AsyncMock()
    return service


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def client(mock_user_service, mock_notification_service, mock_db_session, mock_current_user):
    """Test client with mocks."""
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_notification_service] = lambda: mock_notification_service
    app.dependency_overrides[get_async_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


# ============================================================================
# Tests
# ============================================================================


def test_get_users(client, mock_user_service):
    """Test get_users endpoint."""
    mock_user_service.get_users.return_value = []
    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    mock_user_service.get_users.assert_called_with(skip=0, limit=100)


def test_get_users_forbidden_for_non_admin(client, mock_user_service, mock_current_user):
    """Test get_users is forbidden for non-admin users."""
    mock_current_user.role = "user"

    response = client.get("/api/v1/users/")

    assert response.status_code == 403
    mock_user_service.get_users.assert_not_called()


def test_get_user_stats(client, mock_user_service):
    """Test get_user_stats."""
    mock_user_service.get_user_stats.return_value = {"total": 10}
    response = client.get("/api/v1/users/stats")
    assert response.status_code == 200
    assert response.json()["total"] == 10


def test_get_user_stats_forbidden_for_non_admin(client, mock_user_service, mock_current_user):
    """Test user stats are forbidden for non-admin users."""
    mock_current_user.role = "user"

    response = client.get("/api/v1/users/stats")

    assert response.status_code == 403
    mock_user_service.get_user_stats.assert_not_called()


def test_invite_user_success(client, mock_user_service, mock_current_user):
    """Test invite_user success as admin."""
    mock_current_user.role = "admin"
    new_id = uuid4()
    mock_user_service.invite_user.return_value = {
        "id": new_id,
        "email": "invite@test.com",
        "role": "viewer",
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    payload = {"email": "invite@test.com", "role": "viewer", "name": "Invitee"}
    response = client.post("/api/v1/users/invite", json=payload)

    assert response.status_code == 200
    assert response.json()["email"] == "invite@test.com"
    mock_user_service.invite_user.assert_awaited_once()
    assert mock_user_service.invite_user.await_args.kwargs["actor_role"] == "admin"


def test_manager_cannot_invite_privileged_user(client, mock_user_service, mock_current_user):
    """Managers can invite lower roles but cannot create admins or managers."""
    mock_current_user.role = "manager"

    response = client.post(
        "/api/v1/users/invite", json={"email": "invite@test.com", "role": "admin"}
    )

    assert response.status_code == 403
    mock_user_service.invite_user.assert_not_called()


def test_manager_can_invite_viewer(client, mock_user_service, mock_current_user):
    """Managers can still invite non-privileged users."""
    mock_current_user.role = "manager"
    new_id = uuid4()
    mock_user_service.invite_user.return_value = {
        "id": new_id,
        "email": "viewer@test.com",
        "role": "viewer",
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    response = client.post(
        "/api/v1/users/invite", json={"email": "viewer@test.com", "role": "viewer"}
    )

    assert response.status_code == 200
    mock_user_service.invite_user.assert_awaited_once()
    assert mock_user_service.invite_user.await_args.kwargs["actor_role"] == "manager"


def test_invite_user_forbidden(client, mock_user_service, mock_current_user):
    """Test invite_user forbidden for non-admin."""
    mock_current_user.role = "user"

    payload = {"email": "invite@test.com", "role": "viewer"}
    # Assuming role checks happen in router logic or dependency
    # If dependency override mock_current_user.role = "user", router should fail.
    response = client.post("/api/v1/users/invite", json=payload)

    assert response.status_code == 403


def test_invite_user_error(client, mock_user_service, mock_current_user):
    """Test invite_user with service error (e.g. duplicate)."""
    mock_current_user.role = "admin"
    mock_user_service.invite_user.side_effect = ValueError("User exists")

    payload = {"email": "duplicate@test.com", "role": "viewer"}
    response = client.post("/api/v1/users/invite", json=payload)

    assert response.status_code == 400
    # detail is standard FastAPI exception key
    # Relax assertion to catch potential wrapping or casing issues
    assert "User exists" in str(response.json())


def test_update_current_user_profile(client, mock_user_service, mock_current_user):
    """Test profile update."""
    payload = {"name": "New Name"}  # Use correct field 'name'
    mock_user_service.update_user.return_value = {
        "id": mock_current_user.id,
        "name": "New Name",
        "email": mock_current_user.email,
        "role": mock_current_user.role,
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    response = client.put("/api/v1/users/me", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_search_user_by_email_found(client, mock_user_service):
    """Test user search by email found."""
    found_id = uuid4()
    mock_user = {
        "id": found_id,
        "email": "found@test.com",
        "is_active": True,
        "role": "user",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    mock_user_service.get_user_by_email.return_value = mock_user

    response = client.get("/api/v1/users/search/found@test.com")
    assert response.status_code == 200
    assert response.json()["id"] == str(found_id)


def test_search_user_by_email_not_found(client, mock_user_service):
    """Test user search by email not found."""
    mock_user_service.get_user_by_email.return_value = None

    response = client.get("/api/v1/users/search/missing@test.com")
    assert response.status_code == 404


def test_search_users_list(client, mock_user_service):
    """Test searching users list with filters."""
    mock_user_service.search_users.return_value = []

    response = client.get("/api/v1/users/search?q=test&status=active&role=admin")
    assert response.status_code == 200
    mock_user_service.search_users.assert_called_with(
        "test", skip=0, limit=20, role="admin", is_active=True
    )


def test_search_users_forbidden_filter_for_non_admin(client, mock_user_service, mock_current_user):
    """Test non-admin users cannot use broad user filters."""
    mock_current_user.role = "user"

    response = client.get("/api/v1/users/search?q=test&status=active")

    assert response.status_code == 403
    mock_user_service.search_users.assert_not_called()


def test_search_users_non_admin_only_returns_self(client, mock_user_service, mock_current_user):
    """Test non-admin user search is scoped to the current user."""
    mock_current_user.role = "user"

    response = client.get("/api/v1/users/search?q=test@example.com")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "test@example.com"
    mock_user_service.search_users.assert_not_called()


def test_search_users_non_admin_cannot_enumerate_others(
    client, mock_user_service, mock_current_user
):
    """Test non-admin user search does not expose other users."""
    mock_current_user.role = "user"

    response = client.get("/api/v1/users/search?q=other")

    assert response.status_code == 200
    assert response.json() == []
    mock_user_service.search_users.assert_not_called()


def test_get_user_settings(client, mock_user_service, mock_current_user):
    """Test getting user settings."""
    mock_user_service.get_or_create_settings.return_value = {
        "user_id": mock_current_user.id,
        "theme": "dark",
        "notifications_enabled": True,
    }

    response = client.get("/api/v1/users/me/settings")
    assert response.status_code == 200
    assert response.json()["theme"] == "dark"


def test_update_user_settings(client, mock_user_service, mock_current_user):
    """Test updating user settings."""
    payload = {"theme": "light"}
    mock_user_service.update_settings.return_value = {
        "user_id": mock_current_user.id,
        "theme": "light",
        "notifications_enabled": True,
    }

    response = client.patch("/api/v1/users/me/settings", json=payload)
    assert response.status_code == 200
    assert response.json()["theme"] == "light"


# ============================================================================
# Avatar Upload Tests (Mocking Cloudinary & Local)
# ============================================================================

VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\nminimal"


def test_upload_avatar_local_success(client, mock_user_service, mock_current_user):
    """Test uploading avatar to local storage (Cloudinary disabled)."""
    with (
        patch("routers.users.is_cloudinary_configured", return_value=False),
        patch("routers.users.os.makedirs"),
        patch("routers.users.os.remove") as mock_remove,
        patch("routers.users.os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=VALID_PNG_BYTES)) as mock_file,
    ):
        mock_user_service.update_user.return_value = {
            "id": mock_current_user.id,
            "avatar_url": "/static/uploads/new_uuid.png",
            "email": mock_current_user.email,
            "role": "user",
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        files = {"file": ("avatar.png", VALID_PNG_BYTES, "image/png")}
        response = client.post("/api/v1/users/me/avatar", files=files)

        assert response.status_code == 200
        mock_remove.assert_called()
        mock_file.assert_called()


def test_upload_avatar_cloudinary_success(client, mock_user_service, mock_current_user):
    """Test uploading avatar to Cloudinary."""
    with (
        patch("routers.users.is_cloudinary_configured", return_value=True),
        patch("routers.users.cloudinary_upload_avatar") as mock_cloud_upload,
        patch("routers.users.os.remove") as mock_remove,
        patch("routers.users.os.path.exists", return_value=True),
    ):
        mock_cloud_upload.return_value = {"secure_url": "https://cloudinary.com/new.png"}

        mock_user_service.update_user.return_value = {
            "id": mock_current_user.id,
            "avatar_url": "https://cloudinary.com/new.png",
            "email": mock_current_user.email,
            "role": "user",
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        files = {"file": ("avatar.png", VALID_PNG_BYTES, "image/png")}
        response = client.post("/api/v1/users/me/avatar", files=files)

        assert response.status_code == 200
        # alias="avatar" in schema, so JSON key is 'avatar'
        assert response.json()["avatar"] == "https://cloudinary.com/new.png"
        mock_remove.assert_called()


def test_upload_avatar_cloudinary_fail_fallback(client, mock_user_service, mock_current_user):
    """Test Cloudinary failure falling back to local."""
    with (
        patch("routers.users.is_cloudinary_configured", return_value=True),
        patch("routers.users.cloudinary_upload_avatar", return_value=None),
        patch("builtins.open", mock_open(read_data=VALID_PNG_BYTES)),
    ):
        mock_user_service.update_user.return_value = {
            "id": mock_current_user.id,
            "avatar_url": "/static/uploads/fallback.png",
            "email": mock_current_user.email,
            "role": "user",
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        files = {"file": ("avatar.png", VALID_PNG_BYTES, "image/png")}
        response = client.post("/api/v1/users/me/avatar", files=files)

        assert response.status_code == 200
        assert "/static/uploads/" in response.json()["avatar"]
