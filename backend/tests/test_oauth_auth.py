"""
Tests for OAuth and GitHub Auth functionality.
Tests for Google OAuth, GitHub OAuth, and related authentication utilities.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# Set test environment variables before imports
os.environ["GITHUB_CLIENT_ID"] = "test_github_client_id"
os.environ["GITHUB_CLIENT_SECRET"] = "test_github_client_secret"
os.environ["GOOGLE_CLIENT_ID"] = "test_google_client_id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test_google_client_secret"


class TestGitHubOAuth:
    """Test cases for GitHub OAuth functionality."""

    def test_is_github_oauth_configured_when_configured(self):
        """Test that is_github_oauth_configured returns True when credentials are set."""
        with patch.dict(
            os.environ, {"GITHUB_CLIENT_ID": "test_id", "GITHUB_CLIENT_SECRET": "test_secret"}
        ):
            # Re-import to pick up new env vars
            import importlib

            import utils.github_oauth as github_oauth_module

            importlib.reload(github_oauth_module)

            assert github_oauth_module.is_github_oauth_configured() is True

    def test_is_github_oauth_configured_when_not_configured(self):
        """Test that is_github_oauth_configured returns False when credentials are missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear the specific keys
            env_backup = {}
            if "GITHUB_CLIENT_ID" in os.environ:
                env_backup["GITHUB_CLIENT_ID"] = os.environ.pop("GITHUB_CLIENT_ID")
            if "GITHUB_CLIENT_SECRET" in os.environ:
                env_backup["GITHUB_CLIENT_SECRET"] = os.environ.pop("GITHUB_CLIENT_SECRET")

            try:
                import importlib

                import utils.github_oauth as github_oauth_module

                importlib.reload(github_oauth_module)

                # Should be False when not configured
                assert github_oauth_module.is_github_oauth_configured() == False
            finally:
                # Restore environment
                os.environ.update(env_backup)

    @patch("utils.github_oauth.requests.post")
    def test_exchange_code_for_token_success(self, mock_post):
        """Test successful code exchange for GitHub access token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "gho_test_access_token",
            "token_type": "bearer",
            "scope": "user:email",
        }
        mock_post.return_value = mock_response

        with patch.dict(
            os.environ, {"GITHUB_CLIENT_ID": "test_id", "GITHUB_CLIENT_SECRET": "test_secret"}
        ):
            import importlib

            import utils.github_oauth as github_oauth_module

            importlib.reload(github_oauth_module)

            result = github_oauth_module.exchange_code_for_token("test_authorization_code")
            assert result == "gho_test_access_token"

            # Verify the POST request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://github.com/login/oauth/access_token"

    @patch("utils.github_oauth.requests.post")
    def test_exchange_code_for_token_error_response(self, mock_post):
        """Test code exchange when GitHub returns an error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }
        mock_post.return_value = mock_response

        with patch.dict(
            os.environ, {"GITHUB_CLIENT_ID": "test_id", "GITHUB_CLIENT_SECRET": "test_secret"}
        ):
            import importlib

            import utils.github_oauth as github_oauth_module

            importlib.reload(github_oauth_module)

            result = github_oauth_module.exchange_code_for_token("invalid_code")
            assert result is None

    @patch("utils.github_oauth.requests.post")
    def test_exchange_code_for_token_failed_request(self, mock_post):
        """Test code exchange when the HTTP request fails."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with patch.dict(
            os.environ, {"GITHUB_CLIENT_ID": "test_id", "GITHUB_CLIENT_SECRET": "test_secret"}
        ):
            import importlib

            import utils.github_oauth as github_oauth_module

            importlib.reload(github_oauth_module)

            result = github_oauth_module.exchange_code_for_token("test_code")
            assert result is None

    @patch("utils.github_oauth.requests.get")
    def test_get_github_user_info_success(self, mock_get):
        """Test successful retrieval of GitHub user info."""
        # Mock user info response
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345678,
            "login": "testuser",
            "name": "Test User",
            "email": "testuser@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
        }

        mock_get.return_value = mock_user_response

        from utils.github_oauth import get_github_user_info

        result = get_github_user_info("test_access_token")

        assert result is not None
        assert result["id"] == "12345678"
        assert result["email"] == "testuser@example.com"
        assert result["name"] == "Test User"
        assert result["login"] == "testuser"
        assert result["picture"] == "https://avatars.githubusercontent.com/u/12345678"
        assert result["email_verified"] is True

    @patch("utils.github_oauth.requests.get")
    def test_get_github_user_info_with_private_email(self, mock_get):
        """Test retrieval of GitHub user info when email is private."""
        # First call returns user without email
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345678,
            "login": "testuser",
            "name": "Test User",
            "email": None,
            "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
        }

        # Second call returns emails list
        mock_emails_response = MagicMock()
        mock_emails_response.status_code = 200
        mock_emails_response.json.return_value = [
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "primary@example.com", "primary": True, "verified": True},
        ]

        mock_get.side_effect = [mock_user_response, mock_emails_response]

        from utils.github_oauth import get_github_user_info

        result = get_github_user_info("test_access_token")

        assert result is not None
        assert result["email"] == "primary@example.com"

    @patch("utils.github_oauth.requests.get")
    def test_get_github_user_info_failed_request(self, mock_get):
        """Test GitHub user info retrieval when the request fails."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Bad credentials"
        mock_get.return_value = mock_response

        from utils.github_oauth import get_github_user_info

        result = get_github_user_info("invalid_token")
        assert result is None

    @patch("utils.github_oauth.requests.get")
    def test_verify_github_access_token(self, mock_get):
        """Test verify_github_access_token function."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 12345678,
            "login": "testuser",
            "name": "Test User",
            "email": "testuser@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
        }
        mock_get.return_value = mock_response

        from utils.github_oauth import verify_github_access_token

        result = verify_github_access_token("test_token")

        assert result is not None
        assert result["id"] == "12345678"


class TestGoogleOAuth:
    """Test cases for Google OAuth functionality."""

    def test_is_google_oauth_configured_when_configured(self):
        """Test that is_google_oauth_configured returns True when credentials are set."""
        with patch.dict(
            os.environ, {"GOOGLE_CLIENT_ID": "test_id", "GOOGLE_CLIENT_SECRET": "test_secret"}
        ):
            import importlib

            import utils.google_oauth as google_oauth_module

            importlib.reload(google_oauth_module)

            assert google_oauth_module.is_google_oauth_configured() is True


class TestUserServiceGitHubAuth:
    """Test cases for UserService GitHub authentication methods."""

    @pytest.mark.asyncio
    async def test_create_or_update_github_user_new_user(self, async_session):
        """Test creating a new user via GitHub authentication."""
        from services.async_user_service import AsyncUserService

        user_service = AsyncUserService(async_session)

        user = await user_service.create_or_update_github_user(
            github_id="gh_12345678",
            email="githubuser@example.com",
            name="GitHub User",
            avatar_url="https://avatars.githubusercontent.com/u/12345678",
        )

        assert user is not None
        assert user.email == "githubuser@example.com"
        assert user.name == "GitHub User"
        assert user.github_id == "gh_12345678"
        assert user.avatar_url == "https://avatars.githubusercontent.com/u/12345678"
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_create_or_update_github_user_existing_by_github_id(self, async_session):
        """Test updating an existing user found by GitHub ID."""
        from models.user import User
        from services.async_user_service import AsyncUserService

        # Create existing user with GitHub ID
        existing_user = User(
            email="existing@example.com",
            name="Existing User",
            github_id="gh_existing_123",
            is_active=True,
        )
        async_session.add(existing_user)
        await async_session.commit()

        user_service = AsyncUserService(async_session)

        # Update via GitHub auth
        user = await user_service.create_or_update_github_user(
            github_id="gh_existing_123",
            email="updated@example.com",
            name="Updated User",
            avatar_url="https://new-avatar.url",
        )

        assert user.id == existing_user.id
        assert user.email == "updated@example.com"
        assert user.name == "Updated User"
        assert user.avatar_url == "https://new-avatar.url"

    @pytest.mark.asyncio
    async def test_create_or_update_github_user_link_to_existing_email(self, async_session):
        """Test linking GitHub account to existing user found by email."""
        from models.user import User
        from services.async_user_service import AsyncUserService
        from utils.auth import get_password_hash

        # Create existing user without GitHub ID
        existing_user = User(
            email="emailuser@example.com",
            name="Email User",
            hashed_password=get_password_hash("Password123!"),
            is_active=True,
        )
        async_session.add(existing_user)
        await async_session.commit()

        user_service = AsyncUserService(async_session)

        # Link GitHub account via same email
        user = await user_service.create_or_update_github_user(
            github_id="gh_new_456",
            email="emailuser@example.com",
            name="GitHub Name",
            avatar_url="https://github-avatar.url",
        )

        assert user.id == existing_user.id
        assert user.github_id == "gh_new_456"
        # Name should not be overwritten if user already has one
        assert user.name == "Email User"

    @pytest.mark.asyncio
    async def test_get_user_by_github_id(self, async_session):
        """Test getting user by GitHub ID."""
        from models.user import User
        from services.async_user_service import AsyncUserService

        # Create user with GitHub ID
        github_user = User(
            email="github@example.com",
            name="GitHub User",
            github_id="gh_find_me_123",
            is_active=True,
        )
        async_session.add(github_user)
        await async_session.commit()

        user_service = AsyncUserService(async_session)

        # Find by GitHub ID
        found_user = await user_service.get_user_by_github_id("gh_find_me_123")
        assert found_user is not None
        assert found_user.id == github_user.id

        # Not found
        not_found = await user_service.get_user_by_github_id("nonexistent")
        assert not_found is None


class TestUserServiceGoogleAuth:
    """Test cases for UserService Google authentication methods."""

    @pytest.mark.asyncio
    async def test_create_or_update_google_user_new_user(self, async_session):
        """Test creating a new user via Google authentication."""
        from services.async_user_service import AsyncUserService

        user_service = AsyncUserService(async_session)

        user = await user_service.create_or_update_google_user(
            google_id="google_12345678",
            email="googleuser@example.com",
            name="Google User",
            avatar_url="https://lh3.googleusercontent.com/a/test",
        )

        assert user is not None
        assert user.email == "googleuser@example.com"
        assert user.name == "Google User"
        assert user.google_id == "google_12345678"
        assert user.avatar_url == "https://lh3.googleusercontent.com/a/test"

    @pytest.mark.asyncio
    async def test_create_or_update_google_user_existing_by_google_id(self, async_session):
        """Test updating an existing user found by Google ID."""
        from models.user import User
        from services.async_user_service import AsyncUserService

        # Create existing user with Google ID
        existing_user = User(
            email="existing.google@example.com",
            name="Existing Google User",
            google_id="google_existing_123",
            is_active=True,
        )
        async_session.add(existing_user)
        await async_session.commit()

        user_service = AsyncUserService(async_session)

        # Update via Google auth
        user = await user_service.create_or_update_google_user(
            google_id="google_existing_123",
            email="updated.google@example.com",
            name="Updated Google User",
            avatar_url="https://new-google-avatar.url",
        )

        assert user.id == existing_user.id
        assert user.email == "updated.google@example.com"
        assert user.name == "Updated Google User"

    @pytest.mark.asyncio
    async def test_get_user_by_google_id(self, async_session):
        """Test getting user by Google ID."""
        from models.user import User
        from services.async_user_service import AsyncUserService

        # Create user with Google ID
        google_user = User(
            email="google.find@example.com",
            name="Google Find User",
            google_id="google_find_me_456",
            is_active=True,
        )
        async_session.add(google_user)
        await async_session.commit()

        user_service = AsyncUserService(async_session)

        # Find by Google ID
        found_user = await user_service.get_user_by_google_id("google_find_me_456")
        assert found_user is not None
        assert found_user.id == google_user.id

        # Not found
        not_found = await user_service.get_user_by_google_id("nonexistent")
        assert not_found is None


class TestGitHubAuthEndpoint:
    """Test cases for GitHub auth router endpoint."""

    def test_github_login_not_configured(self, client):
        """Test GitHub login when OAuth is not configured."""
        # Patch at the routers.auth module where it's imported
        with patch("routers.auth.is_github_oauth_configured", return_value=False):
            response = client.post("/api/v1/auth/github", json={"code": "test_code"})

            # Server should return 500 when OAuth is not configured
            assert response.status_code == 500
            response_data = response.json()
            # API uses "message" not "detail" due to exception handler
            assert "message" in response_data
            assert "not configured" in response_data["message"].lower()

    def test_github_login_code_exchange_failed(self, client):
        """Test GitHub login when code exchange fails."""
        with (
            patch("routers.auth.is_github_oauth_configured", return_value=True),
            patch("routers.auth.async_exchange_code_for_token", return_value=None),
        ):
            response = client.post("/api/v1/auth/github", json={"code": "invalid_code"})

            # Should return 401 when authentication fails
            assert response.status_code == 401
            response_data = response.json()
            # API uses "message" not "detail" due to exception handler
            assert "message" in response_data

    def test_github_login_user_info_failed(self, client):
        """Test GitHub login when getting user info fails."""
        with (
            patch("routers.auth.is_github_oauth_configured", return_value=True),
            patch("routers.auth.async_exchange_code_for_token", return_value="valid_access_token"),
            patch("routers.auth.async_get_github_user_info", return_value=None),
        ):
            response = client.post("/api/v1/auth/github", json={"code": "valid_code"})

            assert response.status_code == 401

    def test_github_login_success(self, client):
        """Test successful GitHub login."""
        with (
            patch("routers.auth.is_github_oauth_configured", return_value=True),
            patch("routers.auth.async_exchange_code_for_token", return_value="valid_access_token"),
            patch(
                "routers.auth.async_get_github_user_info",
                return_value={
                    "id": "gh_12345678",
                    "email": "github.success@example.com",
                    "name": "GitHub Success User",
                    "picture": "https://avatars.githubusercontent.com/u/12345678",
                },
            ),
        ):
            response = client.post("/api/v1/auth/github", json={"code": "valid_code"})

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Login successful"
            assert data["user"]["email"] == "github.success@example.com"
            assert data["user"]["name"] == "GitHub Success User"

            # Check cookies are set
            assert "access_token" in response.cookies
            assert "refresh_token" in response.cookies

    def test_github_login_with_access_token(self, client):
        """Test GitHub login with direct access token."""
        with (
            patch("routers.auth.is_github_oauth_configured", return_value=True),
            patch(
                "routers.auth.async_get_github_user_info",
                return_value={
                    "id": "gh_direct_token",
                    "email": "direct.token@example.com",
                    "name": "Direct Token User",
                    "picture": "https://avatars.githubusercontent.com/u/99999999",
                },
            ),
        ):
            response = client.post(
                "/api/v1/auth/github", json={"access_token": "direct_access_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user"]["email"] == "direct.token@example.com"


class TestGoogleAuthEndpoint:
    """Test cases for Google auth router endpoint."""

    def test_google_login_not_configured(self, client):
        """Test Google login when OAuth is not configured."""
        # Patch at the routers.auth module where it's imported
        with patch("routers.auth.is_google_oauth_configured", return_value=False):
            response = client.post("/api/v1/auth/google", json={"id_token": "test_token"})

            # Server should return 500 when OAuth is not configured
            assert response.status_code == 500
            response_data = response.json()
            # API uses "message" not "detail" due to exception handler
            assert "message" in response_data
            assert "not configured" in response_data["message"].lower()

    def test_google_login_invalid_token(self, client):
        """Test Google login with invalid token."""
        with (
            patch("routers.auth.is_google_oauth_configured", return_value=True),
            patch("routers.auth.async_verify_google_id_token", return_value=None),
        ):
            response = client.post("/api/v1/auth/google", json={"id_token": "invalid_token"})

            assert response.status_code == 401

    def test_google_login_email_not_verified(self, client):
        """Test Google login when email is not verified."""
        with (
            patch("routers.auth.is_google_oauth_configured", return_value=True),
            patch(
                "routers.auth.async_verify_google_id_token",
                return_value={
                    "id": "google_123",
                    "email": "unverified@example.com",
                    "name": "Unverified User",
                    "email_verified": False,
                },
            ),
        ):
            response = client.post("/api/v1/auth/google", json={"id_token": "valid_token"})

            # Should return 400 when email is not verified
            assert response.status_code == 400
            response_data = response.json()
            # API uses "message" not "detail" due to exception handler
            assert "message" in response_data
            assert "verified" in response_data["message"].lower()

    def test_google_login_success(self, client):
        """Test successful Google login."""
        with (
            patch("routers.auth.is_google_oauth_configured", return_value=True),
            patch(
                "routers.auth.async_verify_google_id_token",
                return_value={
                    "id": "google_success_123",
                    "email": "google.success@example.com",
                    "name": "Google Success User",
                    "picture": "https://lh3.googleusercontent.com/a/test",
                    "email_verified": True,
                },
            ),
        ):
            response = client.post("/api/v1/auth/google", json={"id_token": "valid_token"})

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Login successful"
            assert data["user"]["email"] == "google.success@example.com"

            # Check cookies are set
            assert "access_token" in response.cookies
            assert "refresh_token" in response.cookies


class TestGithubAuthSchema:
    """Test cases for GithubAuth schema."""

    def test_github_auth_schema_with_code(self):
        """Test GithubAuth schema with authorization code."""
        from schemas.user import GithubAuth

        auth = GithubAuth(code="test_authorization_code")
        assert auth.code == "test_authorization_code"
        assert auth.access_token is None

    def test_github_auth_schema_with_access_token(self):
        """Test GithubAuth schema with access token."""
        from schemas.user import GithubAuth

        auth = GithubAuth(access_token="test_access_token")
        assert auth.access_token == "test_access_token"
        assert auth.code is None

    def test_github_auth_schema_empty(self):
        """Test GithubAuth schema with no fields."""
        from schemas.user import GithubAuth

        auth = GithubAuth()
        assert auth.code is None
        assert auth.access_token is None


class TestIntegration:
    """Integration tests for OAuth flows."""

    def test_github_oauth_full_flow(self, unauthenticated_client):
        """Test complete GitHub OAuth flow from code to authenticated session."""
        client = unauthenticated_client
        with (
            patch("routers.auth.is_github_oauth_configured", return_value=True),
            patch(
                "routers.auth.async_exchange_code_for_token", return_value="access_token_from_code"
            ),
            patch(
                "routers.auth.async_get_github_user_info",
                return_value={
                    "id": "integration_gh_user",
                    "email": "integration@github.example.com",
                    "name": "Integration Test User",
                    "picture": "https://avatars.githubusercontent.com/u/integration",
                },
            ),
        ):
            # Step 1: Exchange code for tokens
            login_response = client.post(
                "/api/v1/auth/github", json={"code": "integration_test_code"}
            )
            assert login_response.status_code == 200

            # Step 2: Access protected endpoint with cookies
            me_response = client.get("/api/v1/auth/me")
            assert me_response.status_code == 200
            user_data = me_response.json()
            assert user_data["email"] == "integration@github.example.com"

    def test_google_oauth_full_flow(self, unauthenticated_client):
        """Test complete Google OAuth flow from token to authenticated session."""
        client = unauthenticated_client
        with (
            patch("routers.auth.is_google_oauth_configured", return_value=True),
            patch(
                "routers.auth.async_verify_google_id_token",
                return_value={
                    "id": "integration_google_user",
                    "email": "integration@google.example.com",
                    "name": "Google Integration User",
                    "picture": "https://lh3.googleusercontent.com/a/integration",
                    "email_verified": True,
                },
            ),
        ):
            # Step 1: Verify Google token and get session
            login_response = client.post(
                "/api/v1/auth/google", json={"id_token": "integration_google_token"}
            )
            assert login_response.status_code == 200

            # Step 2: Access protected endpoint with cookies
            me_response = client.get("/api/v1/auth/me")
            assert me_response.status_code == 200
            user_data = me_response.json()
            assert user_data["email"] == "integration@google.example.com"
