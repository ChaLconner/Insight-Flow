from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import utils.github_oauth
import utils.google_oauth

# ==============================================================================
# GOOGLE OAUTH TESTS
# ==============================================================================


def test_google_verify_id_token_no_client_id():
    with patch("utils.google_oauth.GOOGLE_CLIENT_ID", None):
        result = utils.google_oauth.verify_google_id_token("token")
        assert result is None


@patch("google.oauth2.id_token.verify_oauth2_token")
def test_google_verify_id_token_success(mock_verify):
    with patch("utils.google_oauth.GOOGLE_CLIENT_ID", "client_id_123"):
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "aud": "client_id_123",
            "sub": "google_123",
            "email": "test@gmail.com",
            "name": "Test User",
            "picture": "http://pic.com/1",
            "email_verified": True,
        }

        result = utils.google_oauth.verify_google_id_token("valid_token")

        assert result["id"] == "google_123"
        assert result["email"] == "test@gmail.com"


@patch("google.oauth2.id_token.verify_oauth2_token")
def test_google_verify_id_token_invalid_issuer(mock_verify):
    with patch("utils.google_oauth.GOOGLE_CLIENT_ID", "client_id_123"):
        mock_verify.return_value = {"iss": "bad_issuer", "aud": "client_id_123"}
        result = utils.google_oauth.verify_google_id_token("token")
        assert result is None


@pytest.mark.asyncio
async def test_async_verify_google_access_token():
    with patch("httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "123",
            "email": "test@gmail.com",
            "name": "Test",
            "picture": "pic",
            "email_verified": True,
        }
        mock_get.return_value = mock_response

        result = await utils.google_oauth.async_verify_google_access_token("access_token")

        assert result["email"] == "test@gmail.com"


# ==============================================================================
# GITHUB OAUTH TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_async_exchange_code_for_token_success():
    with (
        patch("utils.github_oauth.GITHUB_CLIENT_ID", "id"),
        patch("utils.github_oauth.GITHUB_CLIENT_SECRET", "secret"),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_post = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = mock_post

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "gh_token_123"}
        mock_post.return_value = mock_response

        token = await utils.github_oauth.async_exchange_code_for_token("code_123")
        assert token == "gh_token_123"


@pytest.mark.asyncio
async def test_async_get_github_user_info_success_public_email():
    with patch("httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # First call (User info)
        user_resp = MagicMock()
        user_resp.status_code = 200
        user_resp.json.return_value = {
            "id": 12345,
            "email": "public@github.com",
            "login": "octocat",
            "avatar_url": "pic_url",
        }

        mock_get.side_effect = [user_resp]

        info = await utils.github_oauth.async_get_github_user_info("token")

        assert info["email"] == "public@github.com"
        assert info["id"] == "12345"


@pytest.mark.asyncio
async def test_async_get_github_user_info_private_email():
    with patch("httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # 1. User info without email
        user_resp = MagicMock()
        user_resp.status_code = 200
        user_resp.json.return_value = {"id": 123, "email": None, "login": "octocat"}

        # 2. Emails endpoint
        emails_resp = MagicMock()
        emails_resp.status_code = 200
        emails_resp.json.return_value = [
            {"email": "private@github.com", "primary": True, "verified": True},
            {"email": "unverified@github.com", "primary": False, "verified": False},
        ]

        mock_get.side_effect = [user_resp, emails_resp]

        info = await utils.github_oauth.async_get_github_user_info("token")

        assert info["email"] == "private@github.com"


@patch("requests.get")
def test_verify_google_access_token(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "sub": "123",
        "email": "sync@gmail.com",
        "name": "Sync User",
        "picture": "http://pic.com/sync",
        "email_verified": True,
    }
    mock_get.return_value = mock_response

    result = utils.google_oauth.verify_google_access_token("valid_token")

    assert result["email"] == "sync@gmail.com"
