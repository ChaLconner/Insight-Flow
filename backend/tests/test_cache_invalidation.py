from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_invalidates_dashboard_and_analytics_for_user():
    from services.cache_invalidation import invalidate_dashboard_and_analytics_cache

    with (
        patch(
            "services.async_dashboard_service.invalidate_dashboard_cache",
            new_callable=AsyncMock,
        ) as dashboard_cache,
        patch(
            "services.async_analytics_service.invalidate_analytics_cache",
            new_callable=AsyncMock,
        ) as analytics_cache,
    ):
        user_id = uuid4()
        await invalidate_dashboard_and_analytics_cache(user_id)

    dashboard_cache.assert_awaited_once_with(user_id)
    analytics_cache.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_cache_invalidation_logs_and_swallows_backend_errors():
    from services.cache_invalidation import invalidate_dashboard_and_analytics_cache

    with (
        patch(
            "services.async_dashboard_service.invalidate_dashboard_cache",
            new_callable=AsyncMock,
            side_effect=RuntimeError("cache unavailable"),
        ),
        patch("services.cache_invalidation.logger.error") as log_error,
    ):
        await invalidate_dashboard_and_analytics_cache()

    log_error.assert_called_once()
