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
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days
REFRESH_TOKEN_EXPIRE_DAYS = 30
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
    response.set_cookie(
        key=ACCESS_TOKEN_KEY,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    response.set_cookie(
        key=REFRESH_TOKEN_KEY,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    if log_user_info:
        logger.info(f"Auth cookies set for user {log_user_info}")
    logger.debug(f"Cookie settings: secure={COOKIE_SECURE}, samesite='lax', httponly=True")


def clear_auth_cookies(response: Response) -> None:
    """
    Clear authentication cookies from the response.

    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(ACCESS_TOKEN_KEY)
    response.delete_cookie(REFRESH_TOKEN_KEY)
    logger.debug("Auth cookies cleared")


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
