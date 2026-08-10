from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.password_reset import PasswordReset
from models.user import User
from services.async_password_reset_service import AsyncPasswordResetService
from utils.auth import verify_password


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
async def test_create_password_reset_token_queue_failure_rolls_back(
    password_reset_service, mock_db_session
):
    email = "test@example.com"
    password_reset_service.user_service.get_user_by_email = AsyncMock(
        return_value=User(id=1, email=email)
    )
    mock_token = MagicMock(spec=PasswordReset)

    with (
        patch(
            "models.password_reset.PasswordReset.create_reset_token",
            return_value=(mock_token, "raw_123"),
        ),
        patch(
            "services.async_password_reset_service.enqueue_job",
            new_callable=AsyncMock,
            side_effect=RuntimeError("queue unavailable"),
        ),
        pytest.raises(RuntimeError, match="queue unavailable"),
    ):
        await password_reset_service.create_password_reset_token(email)

    mock_db_session.rollback.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()


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
async def test_reset_validation_can_lock_token_row(password_reset_service, mock_db_session):
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = result

    with patch("models.password_reset.PasswordReset.hash_token", return_value="hashed"):
        await password_reset_service.validate_reset_token("token", for_update=True)

    statement = mock_db_session.execute.await_args.args[0]
    assert statement._for_update_arg is not None


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
    password_reset_service.user_service.hash_password = AsyncMock(return_value="hashed_pass")

    with (
        patch(
            "services.async_password_reset_service.invalidate_auth_user_cache",
            new=AsyncMock(),
        ) as invalidate_auth_cache,
    ):
        result = await password_reset_service.reset_password(token, new_pass)

        assert result is True
        assert mock_user.hashed_password == "hashed_pass"
        assert mock_user.session_version == 1
        assert mock_reset.used is True
        mock_db_session.commit.assert_called_once()
        invalidate_auth_cache.assert_awaited_once_with(mock_user.id)


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
async def test_reset_password_accepts_persisted_token_from_database(async_session, test_user):
    service = AsyncPasswordResetService(async_session)

    reset_token = await service.create_password_reset_token(test_user.email)

    assert reset_token is not None
    assert await service.validate_reset_token(reset_token.raw_token) is not None

    result = await service.reset_password(reset_token.raw_token, "NewPass123!")

    assert result is True
    assert verify_password("NewPass123!", test_user.hashed_password)


@pytest.mark.asyncio
async def test_send_reset_email_dev_mode(password_reset_service):
    with patch(
        "services.async_password_reset_service.enqueue_job", new_callable=AsyncMock
    ) as mock_enqueue:
        result = await password_reset_service.send_reset_email("test@example.com", "token")
        assert result is True
        mock_enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_reset_email_resend_mode(password_reset_service):
    """Test that reset delivery is persisted as a durable queue job."""
    with patch(
        "services.async_password_reset_service.enqueue_job", new_callable=AsyncMock
    ) as mock_enqueue:
        result = await password_reset_service.send_reset_email("test@example.com", "token")

        assert result is True
        mock_enqueue.assert_awaited_once()
