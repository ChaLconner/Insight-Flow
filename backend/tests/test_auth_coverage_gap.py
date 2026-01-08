from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from main import app
from utils.github_oauth import async_exchange_code_for_token, async_get_github_user_info

# Initialize client
# client = TestClient(app)  # Do not use global client

# ============================================================================
# Utils: github_oauth.py Coverage
# ============================================================================


@pytest.mark.asyncio
async def test_github_oauth_missing_config():
    with patch("utils.github_oauth.GITHUB_CLIENT_ID", None):
        token = await async_exchange_code_for_token("code")
        assert token is None


@pytest.mark.asyncio
async def test_github_oauth_exchange_error_response():
    with (
        patch("utils.github_oauth.GITHUB_CLIENT_ID", "id"),
        patch("utils.github_oauth.GITHUB_CLIENT_SECRET", "secret"),
    ):
        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            token = await async_exchange_code_for_token("code")
            assert token is None


@pytest.mark.asyncio
async def test_github_oauth_exchange_json_error():
    with (
        patch("utils.github_oauth.GITHUB_CLIENT_ID", "id"),
        patch("utils.github_oauth.GITHUB_CLIENT_SECRET", "secret"),
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "bad_verification_code"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            token = await async_exchange_code_for_token("code")
            assert token is None


@pytest.mark.asyncio
async def test_github_oauth_user_info_fetch_error():
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        info = await async_get_github_user_info("token")
        assert info is None


@pytest.mark.asyncio
async def test_github_oauth_user_info_no_verified_email():
    user_resp = MagicMock()
    user_resp.status_code = 200
    user_resp.json.return_value = {"id": 1, "login": "test", "email": None}  # Private email

    emails_resp = MagicMock()
    emails_resp.status_code = 200
    emails_resp.json.return_value = [{"email": "u@e.com", "verified": False, "primary": True}]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [user_resp, emails_resp]
        info = await async_get_github_user_info("token")
        assert info is None


# ============================================================================
# Router: auth.py Edge Cases
# ============================================================================


def test_login_account_locked(unauthenticated_client):
    from dependencies import get_user_service

    mock_service = MagicMock()
    mock_service.authenticate_user = AsyncMock(
        side_effect=ValueError("Account locked due to too many failed attempts")
    )

    app.dependency_overrides[get_user_service] = lambda: mock_service

    response = unauthenticated_client.post(
        "/api/v1/auth/login", json={"email": "locked@test.com", "password": "pwd"}
    )
    assert response.status_code == 403
    assert "Account locked" in response.json()["message"]

    del app.dependency_overrides[get_user_service]


def test_login_inactive_user(unauthenticated_client):
    from dependencies import get_user_service

    mock_service = MagicMock()
    # Mock user but is_active=False
    mock_user = MagicMock()
    mock_user.is_active = False
    mock_service.authenticate_user = AsyncMock(return_value=mock_user)

    app.dependency_overrides[get_user_service] = lambda: mock_service

    response = unauthenticated_client.post(
        "/api/v1/auth/login", json={"email": "inactive@test.com", "password": "pwd"}
    )
    assert response.status_code == 400
    assert "Inactive user" in response.json()["message"]

    del app.dependency_overrides[get_user_service]


def test_login_unverified_email(unauthenticated_client):
    from dependencies import get_user_service

    mock_service = MagicMock()
    mock_user = MagicMock()
    mock_user.is_active = True
    mock_user.is_verified = False
    mock_service.authenticate_user = AsyncMock(return_value=mock_user)

    app.dependency_overrides[get_user_service] = lambda: mock_service

    response = unauthenticated_client.post(
        "/api/v1/auth/login", json={"email": "unverified@test.com", "password": "pwd"}
    )
    assert response.status_code == 403
    assert "Email not verified" in response.json()["message"]

    del app.dependency_overrides[get_user_service]


def test_register_email_exists(unauthenticated_client):
    from dependencies import get_user_service

    mock_service = MagicMock()
    mock_service.get_user_by_email = AsyncMock(return_value=MagicMock())  # Returns User

    app.dependency_overrides[get_user_service] = lambda: mock_service

    data = {
        "email": "exists@test.com",
        "username": "exists",
        "password": "Password123!",
        "first_name": "Test",
        "last_name": "User",
    }
    response = unauthenticated_client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["message"]

    del app.dependency_overrides[get_user_service]


def test_register_missing_password_and_google(unauthenticated_client):
    # Override clearing removed to preserve safe fixtures

    data = {
        "email": "nopass@test.com",
        "username": "nopass",
        "first_name": "Test",
        "last_name": "User",
        # No password, no google_id
    }
    response = unauthenticated_client.post("/api/v1/auth/register", json=data)
    # Validation error from Pydantic? Or from logic?
    # Schema probably allows optional password, but logic checks it.
    # Logic in routers/auth.py:88 checks if not password and not google_id
    assert response.status_code == 400
    assert "Either password or Google ID is required" in response.json()["message"]


def test_register_weak_password(unauthenticated_client):
    from dependencies import get_user_service

    mock_service = MagicMock()
    mock_service.get_user_by_email = AsyncMock(return_value=None)

    app.dependency_overrides[get_user_service] = lambda: mock_service

    data = {
        "email": "weak@test.com",
        "username": "weak",
        "password": "password123",  # Weak (no uppercase/special) but passes pydantic min_length=8
        "first_name": "Test",
        "last_name": "User",
    }

    # We need to ensure validate_password is used. It is imported inside the function in routers/auth.py
    # So we can't easily patch it unless we patch it where it is imported.
    # But since we use integration test (client.post), it will run the real validation logic.

    response = unauthenticated_client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 400
    body = response.json()
    # It might return detail as dict or message string depending on exception handler
    # The code raises HTTPException with detail={"message": ..., "violations": ...}
    # Exception handler converts it to proper response.
    # Assuming standard handler returns detail as is if it's a dict.

    # Check if "Password does not meet" is in message OR detail
    detail = body.get("detail")
    if isinstance(detail, dict):
        assert "Password does not meet" in detail.get("message")
    elif isinstance(detail, str):
        assert "Password does not meet" in detail
    else:
        # Check generalized message
        assert "Password does not meet" in str(body)

    del app.dependency_overrides[get_user_service]


def test_refresh_token_invalid_jti(unauthenticated_client):

    # Mock verify to return payload without user_id
    with patch(
        "routers.auth.async_verify_token_with_blacklist",
        new=AsyncMock(return_value={"jti": "only"}),
    ):
        # Missing sub
        unauthenticated_client.cookies.set("refresh_token", "valid_jwt_structure")
        response = unauthenticated_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["message"]


def test_google_login_not_configured(unauthenticated_client):
    with patch("routers.auth.is_google_oauth_configured", return_value=False):
        response = unauthenticated_client.post("/api/v1/auth/google", json={"id_token": "token"})
        assert response.status_code == 500
        data = response.json()
        assert "Google OAuth is not configured" in data.get("detail", data.get("message"))


def test_github_login_not_configured(unauthenticated_client):
    with patch("routers.auth.is_github_oauth_configured", return_value=False):
        response = unauthenticated_client.post("/api/v1/auth/github", json={"code": "code"})
        assert response.status_code == 500
        data = response.json()
        assert "GitHub OAuth is not configured" in data.get("detail", data.get("message"))
