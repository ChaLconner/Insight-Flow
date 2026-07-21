"""
GitHub OAuth utilities for authenticating users via GitHub.
"""

import os

import httpx

from utils.logger import mask_email, setup_logger

logger = setup_logger("github_oauth")

# Load environment variables
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")


def resolve_github_redirect_uri(redirect_uri: str | None = None) -> str:
    explicit_redirect = (redirect_uri or "").strip()
    if explicit_redirect:
        return explicit_redirect

    configured_redirect = os.getenv("GITHUB_REDIRECT_URI", "").strip()
    if configured_redirect:
        return configured_redirect

    frontend_url = os.getenv("FRONTEND_URL", "").strip()
    if frontend_url:
        return f"{frontend_url.rstrip('/')}/auth/callback/github"

    return "http://localhost:3000/auth/callback/github"


def _extract_access_token(data: dict) -> str | None:
    if "error" in data:
        logger.error(f"GitHub OAuth error: {data.get('error_description', data.get('error'))}")
        return None

    access_token = data.get("access_token")
    if not access_token:
        logger.error("No access token in GitHub response")
        return None

    logger.info("Successfully exchanged code for GitHub access token")
    return str(access_token)


def _select_verified_email(emails: list[dict]) -> str | None:
    primary_email = next(
        (
            email_obj.get("email")
            for email_obj in emails
            if email_obj.get("primary") and email_obj.get("verified")
        ),
        None,
    )
    if primary_email:
        return str(primary_email)

    verified_email = next(
        (email_obj.get("email") for email_obj in emails if email_obj.get("verified")),
        None,
    )
    return str(verified_email) if verified_email else None


def _build_github_user_info(user_data: dict, email: str | None) -> dict | None:
    if not email:
        logger.error("Could not retrieve email from GitHub")
        return None

    logger.info(f"Successfully retrieved GitHub user info for: {mask_email(email)}")
    return {
        "id": str(user_data.get("id")),
        "email": email,
        "name": user_data.get("name") or user_data.get("login"),
        "picture": user_data.get("avatar_url"),
        "login": user_data.get("login"),
        "email_verified": True,  # GitHub only returns verified emails
    }


def exchange_code_for_token(code: str, redirect_uri: str | None = None) -> str | None:
    """
    Exchange GitHub authorization code for access token.

    Args:
        code: Authorization code from GitHub OAuth redirect

    Returns:
        str: Access token if successful, None otherwise
    """
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        logger.error("GitHub OAuth credentials not configured")
        return None

    try:
        response = httpx.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": resolve_github_redirect_uri(redirect_uri),
            },
            timeout=30.0,
        )

        if response.status_code != 200:
            logger.error(f"Failed to exchange code for token: {response.text}")
            return None

        data = response.json()

        return _extract_access_token(data)

    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        return None


def get_github_user_info(access_token: str) -> dict | None:
    """
    Get user information from GitHub API.

    Args:
        access_token: GitHub access token

    Returns:
        Dict: User information if successful, None otherwise
    """
    try:
        # Get user profile
        user_response = httpx.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=30.0,
        )

        if user_response.status_code != 200:
            logger.error(f"Failed to get GitHub user info: {user_response.text}")
            return None

        user_data = user_response.json()

        # Get user email (may need separate request if email is private)
        email = user_data.get("email")

        if not email:
            # Fetch emails from separate endpoint
            emails_response = httpx.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=30.0,
            )

            if emails_response.status_code == 200:
                emails = emails_response.json()
                email = _select_verified_email(emails)

        return _build_github_user_info(user_data, email)

    except Exception as e:
        logger.error(f"Error getting GitHub user info: {e}")
        return None


def verify_github_access_token(access_token: str) -> dict | None:
    """
    Verify GitHub access token and return user information.
    This is an alternative entry point that accepts an access token directly.

    Args:
        access_token: GitHub access token

    Returns:
        Dict: User information if valid, None otherwise
    """
    return get_github_user_info(access_token)


def is_github_oauth_configured() -> bool:
    """
    Check if GitHub OAuth is properly configured.

    Returns:
        bool: True if GitHub OAuth is configured, False otherwise
    """
    return bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)


# ==============================================================================
# ASYNC VERSIONS (for use in async contexts - recommended for FastAPI)
# ==============================================================================


async def async_exchange_code_for_token(code: str, redirect_uri: str | None = None) -> str | None:
    """
    Async version: Exchange GitHub authorization code for access token.
    Uses httpx for non-blocking HTTP requests.

    Args:
        code: Authorization code from GitHub OAuth redirect

    Returns:
        str: Access token if successful, None otherwise
    """
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        logger.error("GitHub OAuth credentials not configured")
        return None

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": resolve_github_redirect_uri(redirect_uri),
                },
            )

        if response.status_code != 200:
            logger.error(f"Failed to exchange code for token: {response.text}")
            return None

        data = response.json()

        return _extract_access_token(data)

    except ImportError:
        logger.warning("httpx not available, falling back to sync version")
        import asyncio

        return await asyncio.to_thread(
            exchange_code_for_token, code, resolve_github_redirect_uri(redirect_uri)
        )
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        return None


async def async_get_github_user_info(access_token: str) -> dict | None:
    """
    Async version: Get user information from GitHub API.
    Uses httpx for non-blocking HTTP requests.

    Args:
        access_token: GitHub access token

    Returns:
        Dict: User information if successful, None otherwise
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get user profile
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )

            if user_response.status_code != 200:
                logger.error(f"Failed to get GitHub user info: {user_response.text}")
                return None

            user_data = user_response.json()

            # Get user email (may need separate request if email is private)
            email = user_data.get("email")

            if not email:
                # Fetch emails from separate endpoint
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )

                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    email = _select_verified_email(emails)

        return _build_github_user_info(user_data, email)

    except ImportError:
        logger.warning("httpx not available, falling back to sync version")
        import asyncio

        return await asyncio.to_thread(get_github_user_info, access_token)
    except Exception as e:
        logger.error(f"Error getting GitHub user info: {e}")
        return None
