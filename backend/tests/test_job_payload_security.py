from unittest.mock import AsyncMock, patch

import pytest

from services.job_handlers import _email_token, _send_email
from services.job_payload_security import decrypt_job_secret, encrypt_job_secret


def test_job_secret_round_trip(monkeypatch):
    monkeypatch.setattr(
        "services.job_payload_security.get_secret_key",
        lambda: "test-secret-key-that-is-long-enough-for-settings",
    )

    protected = encrypt_job_secret("one-time-token")

    assert protected != "one-time-token"
    assert decrypt_job_secret(protected) == "one-time-token"


def test_invalid_job_secret_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "services.job_payload_security.get_secret_key",
        lambda: "test-secret-key-that-is-long-enough-for-settings",
    )

    with pytest.raises(ValueError, match="invalid"):
        decrypt_job_secret("not-a-fernet-token")


def test_legacy_job_token_is_only_read_for_compatibility(caplog):
    assert _email_token({"token": "legacy-token"}) == "legacy-token"
    assert "legacy unprotected" in caplog.text


@pytest.mark.asyncio
async def test_email_handler_decrypts_protected_token(monkeypatch):
    monkeypatch.setattr(
        "services.job_payload_security.get_secret_key",
        lambda: "test-secret-key-that-is-long-enough-for-settings",
    )
    protected = encrypt_job_secret("one-time-token")

    with patch(
        "services.job_handlers.EmailService.send_verification_email",
        new=AsyncMock(return_value=True),
    ) as send_email:
        await _send_email(
            {
                "method": "verification",
                "email": "user@example.com",
                "token_encrypted": protected,
            }
        )

    send_email.assert_awaited_once_with("user@example.com", "one-time-token")
