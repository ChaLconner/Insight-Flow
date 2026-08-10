"""Short-lived cache for the scalar user state required by authentication."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from models.user import User
from services.cache_service import cache_service
from utils.logger import setup_logger

AUTH_USER_CACHE_TTL = 30
AUTH_USER_CACHE_PREFIX = "auth:user:"
logger = setup_logger("auth_cache")

_CACHE_FIELDS = (
    "email",
    "name",
    "first_name",
    "last_name",
    "username",
    "avatar_url",
    "phone",
    "bio",
    "location",
    "website",
    "is_active",
    "is_verified",
    "role",
    "created_at",
    "updated_at",
    "last_login_at",
)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _serialize_user(user: User) -> dict[str, Any] | None:
    """Return only non-secret scalar fields safe for a short-lived cache."""
    if not user.id or not user.email or user.created_at is None or user.updated_at is None:
        return None

    return {
        "user_id": str(user.id),
        "session_version": int(getattr(user, "session_version", 0) or 0),
        **{field: _serialize_value(getattr(user, field, None)) for field in _CACHE_FIELDS},
    }


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _deserialize_user(cached: dict[str, Any]) -> User | None:
    try:
        user_id = uuid.UUID(str(cached["user_id"]))
        session_version = int(cached.get("session_version", 0))
        created_at = _parse_datetime(cached.get("created_at"))
        updated_at = _parse_datetime(cached.get("updated_at"))
        if created_at is None or updated_at is None:
            return None

        values = {
            field: cached.get(field)
            for field in _CACHE_FIELDS
            if field not in {"created_at", "updated_at", "last_login_at"}
        }
        values.update(
            {
                "id": user_id,
                "session_version": session_version,
                "created_at": created_at,
                "updated_at": updated_at,
                "last_login_at": _parse_datetime(cached.get("last_login_at")),
            }
        )
        return User(**values)
    except (KeyError, TypeError, ValueError):
        return None


def _cache_key(user_id: uuid.UUID | str) -> str:
    return f"{AUTH_USER_CACHE_PREFIX}{user_id}"


async def get_cached_auth_user(
    user_id: uuid.UUID | str,
    session_version: int,
) -> User | None:
    try:
        cached = await cache_service.get(_cache_key(user_id))
    except Exception as exc:
        logger.warning(f"Auth cache read failed: {exc}")
        return None
    if not cached:
        return None
    try:
        if int(cached.get("session_version", -1)) != int(session_version):
            return None
    except (TypeError, ValueError):
        return None
    return _deserialize_user(cached)


async def cache_auth_user(user: User) -> None:
    payload = _serialize_user(user)
    if payload is not None:
        try:
            await cache_service.set(_cache_key(user.id), payload, timeout=AUTH_USER_CACHE_TTL)
        except Exception as exc:
            logger.warning(f"Auth cache write failed: {exc}")


async def invalidate_auth_user_cache(user_id: uuid.UUID | str) -> None:
    try:
        await cache_service.delete(_cache_key(user_id))
    except Exception as exc:
        logger.warning(f"Auth cache invalidation failed: {exc}")
