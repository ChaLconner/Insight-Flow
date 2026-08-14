import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from seed_security import require_dev_token_issuance, require_seed_password


def test_seed_password_rejects_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SEED_DATA_PASSWORD", "a" * 32)

    with pytest.raises(RuntimeError, match="Refusing demo-data seeding"):
        require_seed_password()


def test_seed_password_requires_a_strong_operator_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SEED_DATA_PASSWORD", "short")

    with pytest.raises(RuntimeError, match="at least 16 characters"):
        require_seed_password()


def test_token_issuance_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ALLOW_DEV_TOKEN_ISSUANCE", raising=False)

    with pytest.raises(RuntimeError, match="ALLOW_DEV_TOKEN_ISSUANCE=true"):
        require_dev_token_issuance()
