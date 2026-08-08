"""
Authentication utilities for JWT token handling and password management.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

# Using PyJWT instead of python-jose for improved security (CVE-2024-33663, CVE-2024-33664)
import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError

# Import from advanced password security module
from security.password import (
    hash_password as _hash_password,
)
from security.password import (
    verify_password as _verify_password,
)
from utils.logger import setup_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session

logger = setup_logger("auth_utils")

# Load environment variables
load_dotenv()

# JWT Configuration
# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY") or ""
# Allow empty SECRET_KEY in TESTING mode to prevent ImportErrors during test collection
# The tests themselves will inject a mock SECRET_KEY
if not SECRET_KEY and os.getenv("TESTING") != "true":
    raise ValueError(
        "SECRET_KEY environment variable is required for security. Please set it in your .env file."
    )
elif not SECRET_KEY and os.getenv("TESTING") == "true":
    SECRET_KEY = "test_secret_key_placeholder"

ALGORITHM = "HS256"
# Security: Default to 30 minutes for access tokens (recommended practice)
# Note: token_utils.py handles actual token creation with secure defaults
# This value is kept for backwards compatibility with any direct usage
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Supports both bcrypt and argon2id hashes.
    """
    return _verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using Argon2id (PHC winner).
    """
    return _hash_password(password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with JWT ID (jti) for blacklist functionality.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)

    # Add JWT ID (jti) for blacklist functionality
    jti = str(uuid.uuid4())
    to_encode.update(
        {"exp": int(expire.timestamp()), "jti": jti, "iat": int(datetime.now(UTC).timestamp())}
    )

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify and decode a JWT token.
    """

    try:
        if not token:
            raise ValueError("Token is empty or None")

        # Check token structure
        token_parts = token.split(".")
        if len(token_parts) != 3:
            raise ValueError("Invalid token structure")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Absolute Session Timeout Policy (A+ Security)
        # Force re-login after 365 days even if user is active
        # This prevents sessions from living forever
        iat = payload.get("iat")
        if iat:
            session_start = datetime.fromtimestamp(iat, tz=UTC)
            now = datetime.now(UTC)
            MAX_SESSION_DAYS = 365
            if (now - session_start).days > MAX_SESSION_DAYS:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session limit exceeded. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return dict(payload)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (PyJWTError, InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token_with_blacklist(token: str, db_session: "Session") -> dict[str, Any]:
    """
    Verify and decode a JWT token, checking if it's blacklisted.

    Args:
        token: JWT token to verify
        db_session: Database session for blacklist checking

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid, expired, or blacklisted
    """
    # First verify the token normally
    payload = verify_token(token)

    # Check if token is blacklisted
    from models.token_blacklist import TokenBlacklist

    token_jti = payload.get("jti")

    if token_jti and TokenBlacklist.is_token_blacklisted(db_session, token_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def async_verify_token_with_blacklist(
    token: str, db_session: "AsyncSession"
) -> dict[str, Any]:
    """
    Verify and decode a JWT token, checking if it's blacklisted (Async).
    Uses Redis cache to avoid hitting PostgreSQL on every request.
    """
    # First verify the token normally
    payload = verify_token(token)

    # Check if token is blacklisted
    from models.token_blacklist import TokenBlacklist
    from services.cache_service import cache_service

    token_jti = payload.get("jti")

    if token_jti:
        cache_key = f"blacklist:jti:{token_jti}"
        cached_status = await cache_service.get(cache_key)

        if cached_status is not None:
            if cached_status.get("revoked"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            is_revoked = await TokenBlacklist.async_is_token_blacklisted(db_session, token_jti)
            await cache_service.set(
                cache_key, {"revoked": is_revoked}, timeout=3600 if is_revoked else 300
            )

            if is_revoked:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    return payload


def get_token_expiration(token: str) -> datetime | None:
    """
    Extract expiration time from a JWT token after signature verification.

    Args:
        token: JWT token

    Returns:
        datetime: Expiration time of the token, or None if cannot be extracted or signature is invalid
    """
    try:
        # Verify signature while ignoring expiration check to extract exp timestamp securely
        payload_data = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        exp_timestamp = payload_data.get("exp")
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp, tz=UTC)

    except Exception:
        pass
    return None


def authenticate_user(user: Any, password: str) -> bool:
    """
    Authenticate a user by verifying their password.
    """
    if not user:
        return False

    if not user.hashed_password:
        return False

    try:
        result = verify_password(password, user.hashed_password)
        return result
    except Exception:
        return False
