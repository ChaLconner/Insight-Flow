from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from models.token_blacklist import TokenBlacklist


def _result(existing=None):
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    return result


@pytest.mark.asyncio
async def test_async_blacklist_token_claims_new_jti():
    db = AsyncMock()
    db.execute.return_value = _result()

    with (
        patch("models.token_blacklist.secrets.randbelow", return_value=9),
        patch.object(TokenBlacklist, "_invalidate_cache", new=AsyncMock()),
    ):
        claimed = await TokenBlacklist.async_blacklist_token(
            db, "jti-new", datetime.now(UTC) + timedelta(minutes=5)
        )

    assert claimed is True
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_blacklist_token_rejects_existing_jti():
    db = AsyncMock()
    db.execute.return_value = _result(TokenBlacklist(token_jti="jti-used"))

    with (
        patch("models.token_blacklist.secrets.randbelow", return_value=9),
        patch.object(TokenBlacklist, "_invalidate_cache", new=AsyncMock()),
    ):
        claimed = await TokenBlacklist.async_blacklist_token(
            db, "jti-used", datetime.now(UTC) + timedelta(minutes=5)
        )

    assert claimed is False
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_blacklist_token_rejects_concurrent_unique_conflict():
    db = AsyncMock()
    db.execute.return_value = _result()
    db.commit.side_effect = IntegrityError("duplicate key", {}, Exception())

    with (
        patch("models.token_blacklist.secrets.randbelow", return_value=9),
        patch.object(TokenBlacklist, "_invalidate_cache", new=AsyncMock()),
    ):
        claimed = await TokenBlacklist.async_blacklist_token(
            db, "jti-raced", datetime.now(UTC) + timedelta(minutes=5)
        )

    assert claimed is False
    db.rollback.assert_awaited_once()
