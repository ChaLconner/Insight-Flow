from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from dependencies.auth import verify_token_fingerprint


@pytest.mark.asyncio
async def test_trusted_next_ssr_request_skips_browser_ip_comparison():
    request = MagicMock(spec=Request)
    request.headers = {"x-next-server-request": "1"}
    request.client = SimpleNamespace(host="127.0.0.1")

    with (
        patch("security.token_fingerprint.FINGERPRINT_ENABLED", True),
        patch("security.token_fingerprint.verify_fingerprint_claim") as verify_claim,
    ):
        await verify_token_fingerprint(
            request, {"fp": "browser-fingerprint"}, "user-1", AsyncMock()
        )

    verify_claim.assert_not_called()


@pytest.mark.asyncio
async def test_untrusted_next_ssr_marker_does_not_skip_fingerprint_check():
    request = MagicMock(spec=Request)
    request.headers = {"x-next-server-request": "1"}
    request.client = SimpleNamespace(host="203.0.113.10")

    with (
        patch("security.token_fingerprint.FINGERPRINT_ENABLED", True),
        patch(
            "security.token_fingerprint.verify_fingerprint_claim",
            return_value=(True, "match"),
        ) as verify_claim,
    ):
        await verify_token_fingerprint(
            request, {"fp": "browser-fingerprint"}, "user-1", AsyncMock()
        )

    verify_claim.assert_called_once_with(request, "browser-fingerprint")
