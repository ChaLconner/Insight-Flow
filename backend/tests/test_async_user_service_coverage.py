from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from models.user import User
from models.user_settings import UserSettings
from schemas.user import UserCreate, UserSettingsUpdate, UserUpdate
from services.async_user_service import AsyncUserService, escape_like_pattern

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def service(mock_db):
    return AsyncUserService(mock_db)


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_users_filters(service, mock_db):
    # Setup
    users = [User(id=uuid4(), email="a@test.com")]
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = users
    mock_db.execute.return_value = result_mock

    # Test with query, role, is_active
    await service.search_users(query="test", role="admin", is_active=True)

    # Verify execute called
    assert mock_db.execute.call_count == 1
    # Note: verifying exact SQL structure on mocks is hard, but we know it runs


@pytest.mark.asyncio
async def test_get_or_create_settings_existing(service, mock_db):
    settings = UserSettings(user_id=uuid4())
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = settings
    mock_db.execute.return_value = result_mock

    res = await service.get_or_create_settings(settings.user_id)
    assert res == settings
    assert mock_db.add.call_count == 0


@pytest.mark.asyncio
async def test_get_or_create_settings_create_race_condition(service, mock_db):
    user_id = uuid4()

    # First execute returns None (not found)
    # Commit raises IntegrityError (race condition, created by another)
    # Second execute returns Settings (found)

    settings = UserSettings(user_id=user_id)

    # Chain of return values for execute
    # 1. Select -> None
    # 2. Select (in except block) -> settings

    mock_result_none = MagicMock()
    mock_result_none.scalars.return_value.first.return_value = None

    mock_result_found = MagicMock()
    mock_result_found.scalars.return_value.first.return_value = settings

    # We need execute to return different things.
    # Note: getting settings calls execute, then inside except calls execute again.
    mock_db.execute.side_effect = [mock_result_none, mock_result_found]

    mock_db.commit.side_effect = IntegrityError(None, None, Exception("duplicate"))

    res = await service.get_or_create_settings(user_id)

    assert res == settings
    assert mock_db.rollback.call_count == 1
    assert mock_db.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_or_create_settings_fail_final(service, mock_db):
    user_id = uuid4()
    mock_result_none = MagicMock()
    mock_result_none.scalars.return_value.first.return_value = None

    mock_db.execute.return_value = mock_result_none
    # First commit succeeds (no integrity error), but imagine verify fails?
    # Logic: if not settings -> add -> commit -> refresh.
    # If refresh fails? Or logic error?
    # Wait, code says: if not settings -> raise ValueError.

    # To hit ValueError:
    # 1. execute -> None
    # 2. add -> commit -> refresh (success) -> returns object.
    # But if verify still None? (Impossible if flow works)

    # Case: Integrity Error -> Rollback -> execute -> Returns None (Still not found?)
    # This implies race condition failed or something weird.

    mock_db.commit.side_effect = IntegrityError(None, None, Exception("dup"))
    mock_db.execute.return_value = mock_result_none  # Always None

    with pytest.raises(ValueError, match="Could not retrieve user settings"):
        await service.get_or_create_settings(user_id)


@pytest.mark.asyncio
async def test_update_settings_fail(service, mock_db):
    user_id = uuid4()
    settings = UserSettings(user_id=user_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = settings
    mock_db.execute.return_value = mock_result

    mock_db.commit.side_effect = Exception("DB Error")

    update_data = UserSettingsUpdate(theme="light")

    with pytest.raises(ValueError, match="Failed to update settings"):
        await service.update_settings(user_id, update_data)

    assert mock_db.rollback.call_count == 1


@pytest.mark.asyncio
async def test_create_user_integrity_error_username(service, mock_db):
    user_data = UserCreate(email="test@test.com", username="taken")
    mock_db.flush.side_effect = IntegrityError(None, None, Exception("username_key"))

    with pytest.raises(ValueError, match="Username already taken"):
        await service.create_user(user_data)


@pytest.mark.asyncio
async def test_create_user_integrity_error_google(service, mock_db):
    user_data = UserCreate(email="test@test.com")
    mock_db.flush.side_effect = IntegrityError(None, None, Exception("google_id_key"))

    with pytest.raises(ValueError, match="Google account already linked"):
        await service.create_user(user_data)


@pytest.mark.asyncio
async def test_create_user_trial_subscription_failure(service, mock_db):
    user_data = UserCreate(email="test@test.com", plan="pro")

    # Flush the user successfully, then fail while staging the subscription.

    # Simulate DB user logic (mock refresh)
    def refresh_side_effect(obj):
        obj.id = uuid4()

    mock_db.refresh.side_effect = refresh_side_effect

    # Simulate subscription error
    # We can mock Subscription creation raising error or db.add raising error
    # Or db.flush raising an error on the second call.

    mock_db.flush.side_effect = [None, Exception("Sub Error")]

    with (
        patch("services.async_user_service.enqueue_job", new_callable=AsyncMock),
        pytest.raises(ValueError, match="staging subscription"),
    ):
        await service.create_user(user_data)

    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_integrity_error(service, mock_db):
    user = User(id=uuid4(), email="test@test.com")
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    mock_db.commit.side_effect = IntegrityError(None, None, Exception("username"))

    update = UserUpdate(username="newtaken")

    with pytest.raises(ValueError, match="Username already taken"):
        await service.update_user(user.id, update)


@pytest.mark.asyncio
async def test_escape_like_pattern():
    assert escape_like_pattern("test%") == "test\\%"
    assert escape_like_pattern("test_") == "test\\_"
    assert escape_like_pattern("test\\") == "test\\\\"
    assert escape_like_pattern("normal") == "normal"
