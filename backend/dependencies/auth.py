"""
Authentication dependencies for Insight-Flow application.
Moved from routers/auth.py to resolve circular dependencies.
"""

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from dependencies.services import get_user_service
from models.user import User
from services.async_user_service import AsyncUserService
from utils.auth import async_verify_token_with_blacklist
from utils.logger import setup_logger
from utils.token_utils import ACCESS_TOKEN_KEY

logger = setup_logger("auth_dependencies")

# OAuth2 scheme for token authentication
# Set auto_error=False so we can fallback to cookie-based tokens when Authorization header is absent
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def _session_version_matches(payload: dict[str, Any], user: User) -> bool:
    """Reject tokens issued before the user's current session version."""
    try:
        token_version = int(payload.get("sv", 0))
        current_version = int(getattr(user, "session_version", 0) or 0)
    except (TypeError, ValueError):
        return False
    return token_version == current_version


def get_token_from_cookie_or_header(
    request: Request, token: str | None = Depends(oauth2_scheme)
) -> str | None:
    """Get token from Authorization header or HttpOnly cookie."""
    if token:
        return token

    # Fallback to manual header check if OAuth2 scheme didn't catch it
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    return request.cookies.get(ACCESS_TOKEN_KEY)


async def verify_token_fingerprint(request: Request, payload: dict, user_id: str, db: AsyncSession):
    """Verify token fingerprint if present and enabled."""
    stored_fingerprint = payload.get("fp")
    if not stored_fingerprint:
        return

    try:
        from security.token_fingerprint import (
            FINGERPRINT_ENABLED,
            verify_fingerprint_claim,
        )

        if not FINGERPRINT_ENABLED:
            return

        is_valid, reason = verify_fingerprint_claim(request, stored_fingerprint)
        if is_valid:
            return

        logger.warning(f"Token fingerprint mismatch for user {user_id}: {reason}")
        # Log as security audit event
        try:
            from utils.request_security import get_client_ip
            from utils.security_audit import security_audit

            security_audit.log_suspicious_activity(
                ip_address=get_client_ip(request),
                description=f"Token used from different device/network: {reason}",
                user_id=user_id,
                db=db,
            )
            # Commit to ensure log is saved before raising 401
            await db.commit()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalid - please login again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ImportError:
        pass  # Fingerprint module not available
    except HTTPException:
        raise
    except Exception as e:
        logger.debug(f"Fingerprint verification skipped: {e}")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    user_service: AsyncUserService = Depends(get_user_service),
    token: str | None = Depends(get_token_from_cookie_or_header),
) -> Any:
    """Get current authenticated user from token (Cookie or Header)."""
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated - No token provided",
            )

        # Verify token with blacklist checking (Async)
        payload = await async_verify_token_with_blacklist(token, db, expected_type="access")
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

        # A+ Security: Verify token fingerprint (device binding)
        await verify_token_fingerprint(request, payload, user_id, db)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Database lookup
    try:
        user = await user_service.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        if not _session_version_matches(payload, user):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalid - please login again",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database user lookup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    user_service: AsyncUserService = Depends(get_user_service),
    token: str | None = Depends(get_token_from_cookie_or_header),
) -> User | None:
    """Get current authenticated user from token (Cookie or Header) if present."""
    if not token:
        return None

    try:
        # Verify token with blacklist checking (Async)
        payload = await async_verify_token_with_blacklist(token, db, expected_type="access")
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
    except Exception:
        return None

    # Database lookup
    try:
        user = await user_service.get_user_by_id(user_id)
        if user is not None and not _session_version_matches(payload, user):
            return None
        return user
    except Exception:
        return None


async def get_current_active_user_optional(
    current_user: User | None = Depends(get_current_user_optional),
) -> User | None:
    """Get current active user if authenticated."""
    if not current_user:
        return None

    # Ensure active if found
    if not current_user.is_active:
        return None

    return current_user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    # Handle both dict (mock user) and object (database user)
    if isinstance(current_user, dict):
        user_email = current_user.get("email", "unknown")
        is_active = current_user.get("is_active", True)
    else:
        user_email = getattr(current_user, "email", "unknown")
        is_active = getattr(current_user, "is_active", True)

    if not is_active:
        # Log detailed info server-side for debugging
        verification_status = getattr(current_user, "is_verified", "unknown")
        logger.warning(
            f"Inactive user account access attempt: {user_email}, verified: {verification_status}"
        )
        # Return generic error to client (prevent account enumeration)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive. Please contact support.",
        )
    return current_user
