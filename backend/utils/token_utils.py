"""
Token and Cookie utilities for authentication.
Centralizes token creation and cookie management to reduce code duplication.

Security Enhancements:
- Token fingerprinting for device binding (A+ security)
- Prevents token theft by rejecting tokens from different devices/networks
"""

import os
from datetime import timedelta

from fastapi import Request, Response

from utils.auth import create_access_token
from utils.logger import setup_logger

logger = setup_logger("token_utils")

# Configuration
# Security Token Expiration Policy (A+ Security):
# - Access tokens: Short-lived (30 min default) - limits exposure if stolen
# - Refresh tokens: Medium-lived (7 days default) - balance security/UX
# Can be configured via environment variables
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
ACCESS_TOKEN_KEY = "access_token"
REFRESH_TOKEN_KEY = "refresh_token"

# Set secure=True in production, False in development
COOKIE_SECURE = os.getenv("ENVIRONMENT") == "production"


def create_auth_tokens(user_id: str, fingerprint: str | None = None) -> tuple[str, str]:
    """
    Create access and refresh tokens for a user.

    Args:
        user_id: The user's ID as a string
        fingerprint: Optional device fingerprint for token binding (A+ security)

    Returns:
        Tuple of (access_token, refresh_token)
    """
    # Base token data
    token_data: dict[str, str] = {"sub": user_id}
    
    # Add fingerprint if provided (device binding for A+ security)
    if fingerprint:
        token_data["fp"] = fingerprint
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

    # Create refresh token with longer expiration
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_access_token(data=token_data, expires_delta=refresh_token_expires)

    return access_token, refresh_token


def set_auth_cookies(
    response: Response, access_token: str, refresh_token: str, log_user_info: str | None = None
) -> None:
    """
    Set HttpOnly authentication cookies on the response.

    Args:
        response: FastAPI Response object
        access_token: The access token to set
        refresh_token: The refresh token to set
        log_user_info: Optional masked user info for logging
    """
    # For cross-site requests (Vercel <-> Render), SameSite must be 'none'
    # and Secure must be True. If not in production (local dev), we can use
    # 'lax' but 'none' is fine if secure is False.
    # To be safe and compatible with deployed environments:
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    # Critical: Cross-site cookies require Secure=True and SameSite=None
    # But on localhost (http), Secure=True will fail.
    # Logic: If Production -> Secure=True, SameSite=None
    #        If Local -> Secure=False, SameSite=Lax (Standard)

    secure_flag = is_production
    samesite_flag = "none" if is_production else "lax"

    response.set_cookie(
        key=ACCESS_TOKEN_KEY,
        value=access_token,
        httponly=True,
        secure=secure_flag,
        samesite=samesite_flag,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    response.set_cookie(
        key=REFRESH_TOKEN_KEY,
        value=refresh_token,
        httponly=True,
        secure=secure_flag,
        samesite=samesite_flag,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    if log_user_info:
        logger.info(f"Auth cookies set for user {log_user_info}")
    logger.debug(f"Cookie settings: secure={COOKIE_SECURE}, samesite='lax', httponly=True")


def clear_auth_cookies(response: Response) -> None:
    """
    Clear authentication cookies from the response.
    Uses aggressive clearing (Max-Age=0) with matching flags.
    """
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    secure_flag = is_production
    samesite_flag = "none" if is_production else "lax"

    for key in [ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY]:
        response.delete_cookie(
            key=key,
            path="/",
            secure=secure_flag,
            samesite=samesite_flag,
            httponly=True,  # Important to match the set attributes
        )
        # Backup: explicit overwrite (just in case delete_cookie is finicky)
        response.set_cookie(
            key=key,
            value="",
            max_age=0,
            path="/",
            secure=secure_flag,
            samesite=samesite_flag,
            httponly=True,
        )
    logger.debug("Auth cookies cleared aggressive")


def create_and_set_auth_cookies(
    response: Response, 
    user_id: str, 
    log_user_info: str | None = None,
    request: Request | None = None,
) -> tuple[str, str]:
    """
    Create tokens and set cookies in one operation.
    This is a convenience function combining create_auth_tokens and set_auth_cookies.

    Args:
        response: FastAPI Response object
        user_id: The user's ID as a string
        log_user_info: Optional masked user info for logging
        request: Optional request for generating device fingerprint (A+ security)

    Returns:
        Tuple of (access_token, refresh_token)
    """
    fingerprint = None

    # Generate fingerprint if request is provided and feature is enabled
    if request:
        try:
            from security.token_fingerprint import FINGERPRINT_ENABLED, generate_fingerprint_claim

            if FINGERPRINT_ENABLED:
                fingerprint = generate_fingerprint_claim(request)
                logger.debug(f"Generated token fingerprint: {fingerprint[:20]}...")
        except ImportError:
            logger.debug("Token fingerprint module not available")
        except Exception as e:
            logger.warning(f"Failed to generate fingerprint: {e}")

    access_token, refresh_token = create_auth_tokens(user_id, fingerprint)
    set_auth_cookies(response, access_token, refresh_token, log_user_info)
    return access_token, refresh_token
