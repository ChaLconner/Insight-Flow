import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from models.user import User
from services.auth_cache import (
    cache_auth_user,
    get_cached_auth_user,
    invalidate_auth_user_cache,
)
from services.cache_service import CacheService, DisabledCache, cache_service


def _user() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        email="cached@example.com",
        name="Cached User",
        username="cached-user",
        avatar_url="https://example.com/avatar.png",
        is_active=True,
        is_verified=True,
        role="manager",
        session_version=4,
        created_at=now,
        updated_at=now,
        last_login_at=now,
        hashed_password="must-not-be-cached",
    )


@pytest.mark.asyncio
async def test_auth_snapshot_excludes_password_and_checks_session_version():
    user = _user()
    await cache_service.clear()

    await cache_auth_user(user)
    cached = await get_cached_auth_user(user.id, session_version=4)

    assert cached is not None
    assert cached.id == user.id
    assert cached.role == "manager"
    assert cached.hashed_password is None
    assert await get_cached_auth_user(user.id, session_version=3) is None


@pytest.mark.asyncio
async def test_authenticated_user_lookup_uses_snapshot_after_first_miss():
    user = _user()
    await cache_service.clear()
    request = MagicMock()
    db = AsyncMock()
    state_result = MagicMock()
    state_result.one_or_none.return_value = SimpleNamespace(
        session_version=4,
        is_active=True,
        is_verified=True,
        role="manager",
    )
    db.execute = AsyncMock(return_value=state_result)
    user_service = AsyncMock()
    user_service.get_user_by_id.return_value = user

    with (
        patch(
            "dependencies.auth.async_verify_token_with_blacklist",
            new=AsyncMock(return_value={"sub": str(user.id), "sv": 4}),
        ),
        patch("dependencies.auth.verify_token_fingerprint", new=AsyncMock()),
    ):
        from dependencies.auth import get_current_user

        first = await get_current_user(
            request=request,
            db=db,
            user_service=user_service,
            token="access-token",
        )
        second = await get_current_user(
            request=request,
            db=db,
            user_service=user_service,
            token="access-token",
        )

    assert first.id == user.id
    assert second.id == user.id
    user_service.get_user_by_id.assert_awaited_once_with(str(user.id))
    # The cache-miss path uses the full user row as authoritative state; only
    # the cache-hit path needs the smaller revocation-state query.
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_stale_auth_snapshot_cannot_bypass_session_version_change():
    user = _user()
    request = MagicMock()
    db = AsyncMock()
    state_result = MagicMock()
    state_result.one_or_none.return_value = SimpleNamespace(
        session_version=5,
        is_active=True,
        is_verified=True,
        role="manager",
    )
    db.execute = AsyncMock(return_value=state_result)
    user_service = AsyncMock()

    with (
        patch(
            "dependencies.auth.async_verify_token_with_blacklist",
            new=AsyncMock(return_value={"sub": str(user.id), "sv": 4}),
        ),
        patch("dependencies.auth.verify_token_fingerprint", new=AsyncMock()),
        patch(
            "dependencies.auth.get_cached_auth_user",
            new=AsyncMock(return_value=user),
        ),
        pytest.raises(HTTPException, match="Session invalid"),
    ):
        from dependencies.auth import get_current_user

        await get_current_user(
            request=request,
            db=db,
            user_service=user_service,
            token="access-token",
        )

    user_service.get_user_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_negative_blacklist_cache_cannot_bypass_database_revocation():
    """A cached non-revoked result must never override the blacklist database."""
    from models.token_blacklist import TokenBlacklist
    from utils.auth import async_verify_token_with_blacklist

    db = AsyncMock()
    token_payload = {"jti": "stale-jti", "sub": str(uuid.uuid4()), "type": "access"}

    with (
        patch("utils.auth.verify_token", return_value=token_payload),
        patch.object(
            cache_service,
            "get",
            new=AsyncMock(return_value={"revoked": False}),
        ),
        patch.object(
            TokenBlacklist,
            "async_is_token_blacklisted",
            new=AsyncMock(return_value=True),
        ) as is_revoked,
        pytest.raises(HTTPException, match="Token has been revoked"),
    ):
        await async_verify_token_with_blacklist("token", db, expected_type="access")

    is_revoked.assert_awaited_once_with(db, "stale-jti")


@pytest.mark.asyncio
async def test_cache_enabled_false_uses_explicit_disabled_backend():
    settings = MagicMock()
    settings.cache.enabled = False
    settings.cache.redis_url = None
    settings.cache.redis_password = None
    settings.cache.default_timeout = 60

    service = object.__new__(CacheService)
    with patch("services.cache_service.get_settings", return_value=settings):
        service._initialize()

    assert isinstance(service.backend, DisabledCache)
    assert await service.get("disabled-key") is None
    await service.set("disabled-key", {"value": True})
    assert await service.get("disabled-key") is None
    # Rate limiting remains available through the local fallback counter.
    assert await service.increment_with_window("disabled-rate-key", 60) == 1
    assert await service.get("disabled-rate-key") is None


@pytest.mark.asyncio
async def test_auth_cache_failures_fall_back_to_database_path():
    user = _user()
    with (
        patch.object(
            cache_service,
            "get",
            new=AsyncMock(side_effect=RuntimeError("cache unavailable")),
        ),
        patch.object(
            cache_service,
            "set",
            new=AsyncMock(side_effect=RuntimeError("cache unavailable")),
        ),
        patch.object(
            cache_service,
            "delete",
            new=AsyncMock(side_effect=RuntimeError("cache unavailable")),
        ),
    ):
        assert await get_cached_auth_user(user.id, session_version=4) is None
        await cache_auth_user(user)
        await invalidate_auth_user_cache(user.id)
