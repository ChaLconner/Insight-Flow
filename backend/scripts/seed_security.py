"""Safety checks shared by development and CI data-seeding scripts."""

from __future__ import annotations

import os

_SEED_PASSWORD_ENV_VARS = ("SEED_DATA_PASSWORD", "DEMO_USER_PASSWORD", "E2E_USER_PASSWORD")


def _environment() -> str:
    return os.getenv("ENVIRONMENT", "development").strip().lower()


def _reject_production(operation: str) -> None:
    if _environment() in {"prod", "production"}:
        raise RuntimeError(f"Refusing {operation} while ENVIRONMENT is production.")


def require_seed_password() -> str:
    """Return an operator-provided seed password and reject unsafe defaults."""
    _reject_production("demo-data seeding")

    for variable_name in _SEED_PASSWORD_ENV_VARS:
        password = os.getenv(variable_name)
        if password:
            if len(password) < 16:
                raise RuntimeError(
                    f"{variable_name} must contain at least 16 characters for seeded users."
                )
            return password

    variables = ", ".join(_SEED_PASSWORD_ENV_VARS)
    raise RuntimeError(f"Set one of {variables} before running a data-seeding script.")


def require_dev_token_issuance() -> None:
    """Require an explicit development-only opt-in before minting a token."""
    _reject_production("development token issuance")
    if os.getenv("ALLOW_DEV_TOKEN_ISSUANCE", "").strip().lower() != "true":
        raise RuntimeError(
            "Set ALLOW_DEV_TOKEN_ISSUANCE=true to run the development token utility."
        )
