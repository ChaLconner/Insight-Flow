"""
Token and Cookie utilities for authentication.
Centralizes token creation and cookie management to reduce code duplication.
"""

import os
from datetime import timedelta

from fastapi import Response

from utils.auth import create_access_token
from utils.logger import setup_logger

logger = setup_logger("token_utils")

# Configuration
# Security: Short-lived access tokens (30 min), long-lived refresh tokens (30 days)
# This allows seamless user experience while limiting exposure if access token is stolen
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes (recommended security practice)
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days (user stays logged in)
ACCESS_TOKEN_KEY = "access_token"
REFRESH_TOKEN_KEY = "refresh_token"

# Set secure=True in production, False in development
COOKIE_SECURE = os.getenv("ENVIRONMENT") == "production"


def create_auth_tokens(user_id: str) -> tuple[str, str]:
    """
    Create access and refresh tokens for a user.

    Args:
        user_id: The user's ID as a string

    Returns:
        Tuple of (access_token, refresh_token)
    """
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user_id}, expires_delta=access_token_expires)

    # Create refresh token with longer expiration
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_access_token(data={"sub": user_id}, expires_delta=refresh_token_expires)

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
    # For cross-site requests (Vercel <-> Render), SameSite must be 'none' and Secure must be True
    # If not in production (local dev), we can use 'lax' but 'none' is fine if secure is False (though 'none' usually requires secure=True)
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
    response: Response, user_id: str, log_user_info: str | None = None
) -> tuple[str, str]:
    """
    Create tokens and set cookies in one operation.
    This is a convenience function combining create_auth_tokens and set_auth_cookies.

    Args:
        response: FastAPI Response object
        user_id: The user's ID as a string
        log_user_info: Optional masked user info for logging

    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_token, refresh_token = create_auth_tokens(user_id)
    set_auth_cookies(response, access_token, refresh_token, log_user_info)
    return access_token, refresh_token
