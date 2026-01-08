from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.async_user_service import AsyncUserService


# Fixtures
@pytest.fixture
def mock_db_session():
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def user_service(mock_db_session):
    return AsyncUserService(mock_db_session)


@pytest.fixture
def mock_email_service():
    with patch("services.async_user_service.EmailService") as mock:
        mock.send_verification_email = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_verify_email_success(user_service, mock_db_session):
    token = "valid_token"
    # User with matching hashed token
    user = User(
        email="test@example.com",
        verification_token="hashed_token",
        verification_token_expires_at=None,  # Not expired
    )

    res = MagicMock()
    res.scalars.return_value.first.return_value = user
    mock_db_session.execute.return_value = res

    with patch.object(user_service, "_hash_token", return_value="hashed_token"):
        result = await user_service.verify_email(token)

        assert result is True
        assert user.is_verified is True
        assert user.verification_token is None
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_verify_email_expired(user_service, mock_db_session):
    token = "valid_token"
    from datetime import UTC, datetime, timedelta

    # User with expired token
    expired_time = datetime.now(UTC) - timedelta(hours=1)
    user = User(
        email="test@example.com",
        verification_token="hashed_token",
        verification_token_expires_at=expired_time,
        is_verified=False,  # Explicitly set false
    )

    res = MagicMock()
    res.scalars.return_value.first.return_value = user
    mock_db_session.execute.return_value = res

    with patch.object(user_service, "_hash_token", return_value="hashed_token"):
        result = await user_service.verify_email(token)

        # Should verify but fail due to expiration
        assert result is False
        assert user.is_verified is False
        mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_resend_verification_email_success(user_service, mock_db_session, mock_email_service):
    email = "test@example.com"
    user = User(email=email, is_verified=False)

    # Use AsyncMock from unittest.mock, not pytest
    user_service.get_user_by_email = AsyncMock(return_value=user)

    with patch.object(user_service, "_hash_token", return_value="new_hashed_token"):
        result = await user_service.resend_verification_email(email)

        assert result is True
        assert user.verification_token == "new_hashed_token"
        assert user.verification_token_expires_at is not None
        mock_db_session.commit.assert_called_once()
        mock_email_service.send_verification_email.assert_called_once()


@pytest.mark.asyncio
async def test_resend_verification_already_verified(
    user_service, mock_db_session, mock_email_service
):
    email = "verified@example.com"
    user = User(email=email, is_verified=True)

    user_service.get_user_by_email = AsyncMock(return_value=user)

    result = await user_service.resend_verification_email(email)

    # Should return True but not send email or update DB
    assert result is True
    mock_db_session.commit.assert_not_called()
    mock_email_service.send_verification_email.assert_not_called()
