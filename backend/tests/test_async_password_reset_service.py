from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.password_reset import PasswordReset
from models.user import User
from services.async_password_reset_service import AsyncPasswordResetService


@pytest.fixture
def password_reset_service(mock_db_session):
    return AsyncPasswordResetService(mock_db_session)


@pytest.mark.asyncio
async def test_create_password_reset_token_success(password_reset_service, mock_db_session):
    email = "test@example.com"
    user = User(id=1, email=email)

    # Mock user exists using user_service dependency directly or by patching its method
    # The service initializes self.user_service = AsyncUserService(db)
    # We can patch get_user_by_email on the instance's user_service
    password_reset_service.user_service.get_user_by_email = AsyncMock(return_value=user)

    # Mock Token creation
    mock_token = MagicMock(spec=PasswordReset)
    mock_token.raw_token = "raw_123"
    with patch(
        "models.password_reset.PasswordReset.create_reset_token",
        return_value=(mock_token, "raw_123"),
    ):
        result = await password_reset_service.create_password_reset_token(email)

        assert result == mock_token
        assert result.raw_token == "raw_123"
        mock_db_session.execute.assert_called_once()  # Should call update to invalidate
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_password_reset_token_user_not_found(password_reset_service, mock_db_session):
    email = "notfound@example.com"

    password_reset_service.user_service.get_user_by_email = AsyncMock(return_value=None)

    result = await password_reset_service.create_password_reset_token(email)

    assert result is None
    mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_validate_token_success(password_reset_service, mock_db_session):
    token_str = "valid_token"
    mock_reset = MagicMock(spec=PasswordReset)
    mock_reset.is_expired.return_value = False

    res = MagicMock()
    res.scalars.return_value.first.return_value = mock_reset
    mock_db_session.execute.return_value = res

    with patch("models.password_reset.PasswordReset.hash_token", return_value="hashed"):
        result = await password_reset_service.validate_reset_token(token_str)
        assert result == mock_reset


@pytest.mark.asyncio
async def test_validate_token_not_found(password_reset_service, mock_db_session):
    res = MagicMock()
    res.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = res

    with patch("models.password_reset.PasswordReset.hash_token", return_value="hashed"):
        result = await password_reset_service.validate_reset_token("invalid")
        assert result is None


@pytest.mark.asyncio
async def test_validate_token_expired(password_reset_service, mock_db_session):
    mock_reset = MagicMock(spec=PasswordReset)
    mock_reset.is_expired.return_value = True

    res = MagicMock()
    res.scalars.return_value.first.return_value = mock_reset
    mock_db_session.execute.return_value = res

    with patch("models.password_reset.PasswordReset.hash_token", return_value="hashed"):
        result = await password_reset_service.validate_reset_token("expired")
        assert result is None


@pytest.mark.asyncio
async def test_reset_password_success(password_reset_service, mock_db_session):
    token = "valid_token"
    new_pass = "new_pass"
    email = "test@example.com"

    mock_reset = MagicMock(spec=PasswordReset)
    mock_reset.email = email

    # Mock validation
    password_reset_service.validate_reset_token = AsyncMock(return_value=mock_reset)

    # Mock user fetch
    mock_user = MagicMock(spec=User)
    password_reset_service.user_service.get_user_by_email = AsyncMock(return_value=mock_user)

    with patch("utils.auth.get_password_hash", return_value="hashed_pass"):
        result = await password_reset_service.reset_password(token, new_pass)

        assert result is True
        assert mock_user.hashed_password == "hashed_pass"
        assert mock_reset.used is True
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_invalid(password_reset_service):
    password_reset_service.validate_reset_token = AsyncMock(return_value=None)
    result = await password_reset_service.reset_password("invalid", "pass")
    assert result is False


@pytest.mark.asyncio
async def test_reset_password_user_not_found(password_reset_service, mock_db_session):
    mock_reset = MagicMock(spec=PasswordReset)
    mock_reset.email = "test@example.com"

    password_reset_service.validate_reset_token = AsyncMock(return_value=mock_reset)
    password_reset_service.user_service.get_user_by_email = AsyncMock(return_value=None)

    result = await password_reset_service.reset_password("valid", "pass")
    assert result is False


@pytest.mark.asyncio
async def test_send_reset_email_dev_mode(password_reset_service):
    # Mock environment
    with patch("os.getenv") as mock_env:

        def env_val(key, default=None):
            if key == "ENVIRONMENT":
                return "development"
            return default

        mock_env.side_effect = env_val

        result = await password_reset_service.send_reset_email("test@example.com", "token")
        assert result is True


@pytest.mark.asyncio
async def test_send_reset_email_resend_mode(password_reset_service):
    """
    Test that send_reset_email returns immediately (fire-and-forget pattern).
    The actual email sending via Resend API happens in background task.
    """
    with (
        patch("os.getenv") as mock_env,
        patch("utils.background_tasks.fire_and_forget") as mock_fire_and_forget,
    ):
        mock_env.return_value = "configured_value"  # Return truthy for all env vars

        result = await password_reset_service.send_reset_email("test@example.com", "token")

        # Should return True immediately (email queued, not sent)
        assert result is True
        # Should have called fire_and_forget with the internal email coroutine
        mock_fire_and_forget.assert_called_once()
