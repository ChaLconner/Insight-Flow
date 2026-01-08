import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.user_settings import UserSettings
from schemas.user import UserCreate, UserLogin, UserSettingsUpdate
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


@pytest.fixture
def mock_auth_utils():
    with (
        patch("services.async_user_service.get_password_hash") as mock_hash,
        patch("services.async_user_service.verify_password") as mock_verify,
        patch("services.async_user_service.authenticate_user") as mock_auth_user,
    ):
        mock_hash.return_value = "hashed_secret"
        mock_verify.return_value = True
        mock_auth_user.return_value = True
        yield {"hash": mock_hash, "verify": mock_verify, "auth": mock_auth_user}


@pytest.fixture
def mock_validators():
    with patch("services.async_user_service.validate_password_strength") as mock:
        yield mock


# Tests


@pytest.mark.asyncio
async def test_create_user_success(
    user_service, mock_db_session, mock_email_service, mock_auth_utils, mock_validators
):
    user_data = UserCreate(
        email="test@example.com",
        password="StrongPassword123!",
        first_name="John",
        last_name="Doe",
        username="johndoe",
    )

    # Mock loop for hash_password
    with patch("asyncio.get_event_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(return_value="hashed_secret")

        user = await user_service.create_user(user_data)

        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_secret"
        assert user.verification_token is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_email_service.send_verification_email.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_user_success(user_service, mock_db_session, mock_auth_utils):
    login_data = UserLogin(email="test@example.com", password="password")

    # Mock existing user
    user = User(id=uuid.uuid4(), email="test@example.com", hashed_password="hashed_secret")
    res = MagicMock()
    res.scalars.return_value.first.return_value = user
    mock_db_session.execute.return_value = res

    mock_auth_utils["auth"].return_value = True

    authenticated_user = await user_service.authenticate_user(login_data)

    assert authenticated_user is user
    mock_db_session.add.assert_called_once()  # Log auth attempt


@pytest.mark.asyncio
async def test_authenticate_user_locked(user_service, mock_db_session):
    login_data = UserLogin(email="test@example.com", password="password")

    # User locked in future
    future = datetime.now(UTC) + timedelta(minutes=10)
    user = User(id=uuid.uuid4(), email="test@example.com", locked_until=future)

    res = MagicMock()
    res.scalars.return_value.first.return_value = user
    mock_db_session.execute.return_value = res

    with pytest.raises(ValueError, match="Account locked"):
        await user_service.authenticate_user(login_data)


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(user_service, mock_db_session, mock_auth_utils):
    login_data = UserLogin(email="test@example.com", password="wrong")

    user = User(id=uuid.uuid4(), email="test@example.com", failed_login_attempts=0)
    res = MagicMock()
    res.scalars.return_value.first.return_value = user
    mock_db_session.execute.return_value = res

    mock_auth_utils["auth"].return_value = False

    auth_result = await user_service.authenticate_user(login_data)

    assert auth_result is None
    assert user.failed_login_attempts == 1
    assert mock_db_session.commit.call_count >= 1  # Update attempts


@pytest.mark.asyncio
async def test_change_password_success(
    user_service, mock_db_session, mock_auth_utils, mock_validators
):
    uid = uuid.uuid4()
    user = User(id=uid, email="test@example.com", hashed_password="old_hash")

    res = MagicMock()
    res.scalars.return_value.first.return_value = user
    mock_db_session.execute.return_value = res

    # Mock verify old password
    mock_auth_utils["verify"].return_value = True

    # Mock hash new password
    with patch("asyncio.get_event_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(return_value="new_hash")

        result = await user_service.change_password(uid, "old_pass", "new_strong_pass")

        assert result is True
        assert user.hashed_password == "new_hash"
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_or_update_google_user_new(user_service, mock_db_session, mock_email_service):
    # Mock not found by Google ID nor Email
    # Ensure scalars returns a mock, not coroutine (if execute is AsyncMock, return_value is Sync Mock by default unless specified)
    # But here we need scalars() to return a mock that has first()
    # If execute() awaits to return_value, return_value is MagicMock.
    # return_value.scalars is MagicMock (or method returning MagicMock).
    # return_value.scalars().first()

    # We'll explicit set the chain
    res = MagicMock()
    res.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = res

    # Test
    with patch("asyncio.get_event_loop"):
        # Avoid create_user calling real hash (though no password passed)
        # create_user has logic: only hash if user_data.password is set.
        # UserCreate default password is None? No, but google user creation passes user_data without password.

        await user_service.create_or_update_google_user(
            google_id="gid_123",
            email="google@test.com",
            name="Google User",
            avatar_url="http://avatar",
        )

        # Should call create_user logic which adds to DB
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_or_update_google_user_existing_linked(user_service, mock_db_session):
    # Found by Google ID
    user = User(id=uuid.uuid4(), google_id="gid_123", email="old@test.com", name="Old Name")

    res = MagicMock()
    res.scalars.return_value.first.return_value = user
    # get_user_by_google_id returns user
    mock_db_session.execute.return_value = res

    updated = await user_service.create_or_update_google_user(
        google_id="gid_123", email="new@test.com", name="New Name"
    )

    assert updated.email == "new@test.com"
    assert updated.name == "New Name"
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_stats(user_service, mock_db_session):
    # Mock result row: (total, active, admins, managers, members, viewers)
    row = MagicMock()
    row.total = 10
    row.active = 8
    row.admins = 2
    row.managers = 1
    row.members = 6
    row.viewers = 1

    res = MagicMock()
    res.first.return_value = row
    mock_db_session.execute.return_value = res

    stats = await user_service.get_user_stats()

    assert stats["total"] == 10
    assert stats["active"] == 8
    assert stats["admins"] == 2


@pytest.mark.asyncio
async def test_get_or_create_settings_existing(user_service, mock_db_session):
    uid = uuid.uuid4()
    settings = UserSettings(user_id=uid, theme="dark")

    res = MagicMock()
    res.scalars.return_value.first.return_value = settings
    mock_db_session.execute.return_value = res

    result = await user_service.get_or_create_settings(uid)

    assert result.theme == "dark"
    # Should not add new one
    mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_settings_new(user_service, mock_db_session):
    uid = uuid.uuid4()

    # First call returns None
    res = MagicMock()
    res.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = res

    result = await user_service.get_or_create_settings(uid)

    assert result.user_id == uid
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_settings(user_service, mock_db_session):
    uid = uuid.uuid4()
    settings = UserSettings(user_id=uid, theme="light")
    # Object that would be returned by UPDATE ... RETURNING
    updated_settings = UserSettings(user_id=uid, theme="dark", notification_preferences={"enabled": True})

    # Mock UPDATE result returning the settings (success path)
    res = MagicMock()
    res.scalars.return_value.first.return_value = updated_settings
    mock_db_session.execute.return_value = res

    user_service.get_or_create_settings = AsyncMock(return_value=settings)

    update_data = UserSettingsUpdate(theme="dark", notification_preferences={"enabled": True})

    updated = await user_service.update_settings(uid, update_data)

    assert updated.theme == "dark"
    assert updated.notification_preferences == {"enabled": True}
    mock_db_session.commit.assert_called_once()
