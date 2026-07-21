"""
Google OAuth utilities for verifying Google ID tokens.
Includes async versions for non-blocking I/O.
"""

import os

import google.auth.transport.requests
from google.oauth2 import id_token

from utils.logger import mask_email, setup_logger

logger = setup_logger("google_oauth")

# Load environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


def verify_google_id_token(token: str) -> dict | None:
    """
    Verify Google ID token and return user information.
    """
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID environment variable not set")
        return None

    try:
        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(
            token, google.auth.transport.requests.Request(), GOOGLE_CLIENT_ID
        )

        # Check if the token is valid
        if idinfo.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            logger.error(f"Invalid token issuer: {idinfo.get('iss')}")
            return None

        # Check if the audience matches our client ID
        if idinfo.get("aud") != GOOGLE_CLIENT_ID:
            logger.error(f"Invalid token audience: {idinfo.get('aud')}")
            return None

        logger.info(
            f"Successfully verified Google ID token for user: {mask_email(idinfo.get('email'))}"
        )

        return {
            "id": idinfo.get("sub"),
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False),
        }

    except Exception as e:
        logger.error(f"Error verifying Google ID token: {e}")
        return None


def verify_google_access_token(access_token: str) -> dict | None:
    """
    Verify Google access token and return user information.
    """
    import httpx

    try:
        response = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

        if response.status_code != 200:
            logger.error(f"Failed to verify access token: {response.text}")
            return None

        user_info = response.json()
        logger.info(
            f"Successfully verified Google access token for user: {mask_email(user_info.get('email'))}"
        )

        return {
            "id": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "email_verified": user_info.get("email_verified", False),
        }
    except Exception as e:
        logger.error(f"Error verifying Google access token: {e}")
        return None


async def async_verify_google_id_token(token: str) -> dict | None:
    """
    Async version: Verify Google ID token.
    Uses asyncio.to_thread for the library call as it might do blocking networkcert fetches.
    """
    import asyncio

    return await asyncio.to_thread(verify_google_id_token, token)


async def async_verify_google_access_token(access_token: str) -> dict | None:
    """
    Async version: Verify Google access token.
    Uses httpx for non-blocking requests.
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                logger.error(f"Failed to verify access token: {response.text}")
                return None

            user_info = response.json()
            logger.info(
                f"Successfully verified Google access token for user: {mask_email(user_info.get('email'))}"
            )

            return {
                "id": user_info.get("sub"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "email_verified": user_info.get("email_verified", False),
            }
    except Exception as e:
        logger.error(f"Error verifying Google access token: {e}")
        return None


def is_google_oauth_configured() -> bool:
    """
    Check if Google OAuth is properly configured.
    """
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
