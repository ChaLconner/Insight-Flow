"""
Authentication dependencies for Insight-Flow application.
Moved from routers/auth.py to resolve circular dependencies.
"""

from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from dependencies.services import get_user_service
from models.user import User
from services.async_user_service import AsyncUserService
from services.auth_cache import cache_auth_user, get_cached_auth_user
from utils.auth import async_verify_token_with_blacklist
from utils.logger import setup_logger
from utils.request_security import is_trusted_proxy
from utils.token_utils import ACCESS_TOKEN_KEY

logger = setup_logger("auth_dependencies")

# OAuth2 scheme for token authentication
# Set auto_error=False so we can fallback to cookie-based tokens when Authorization header is absent
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
SSR_REQUEST_HEADER = "x-next-server-request"


def _session_version_matches(payload: dict[str, Any], user: User) -> bool:
    """Reject tokens issued before the user's current session version."""
    try:
        token_version = int(payload.get("sv", 0))
        current_version = int(getattr(user, "session_version", 0) or 0)
    except (TypeError, ValueError):
        return False
    return token_version == current_version


async def _get_authoritative_auth_state(
    db: AsyncSession,
    user_id: str,
    token_session_version: int,
) -> Any:
    """Read security-sensitive user state directly from the database."""
    try:
        normalized_user_id = UUID(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    result = await db.execute(
        select(User.session_version, User.is_active, User.is_verified, User.role).where(
            User.id == normalized_user_id
        )
    )
    state = result.one_or_none()
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    try:
        current_session_version = int(state.session_version or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if current_session_version != token_session_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalid - please login again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return state


def _apply_authoritative_auth_state(user: User, state: Any) -> None:
    """Overlay security-sensitive fields on a cached user snapshot."""
    user.session_version = int(state.session_version or 0)
    user.is_active = state.is_active
    user.is_verified = state.is_verified
    user.role = state.role


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

        # Next.js cannot preserve the browser socket across a server-side
        # render fetch. Accept the signed token through this explicitly marked
        # internal hop, but only when the immediate peer is a configured
        # trusted proxy. proxy.ts strips client-supplied copies of the marker.
        direct_ip = request.client.host if request.client else None
        if (
            request.headers.get(SSR_REQUEST_HEADER) == "1"
            and direct_ip
            and is_trusted_proxy(direct_ip)
        ):
            logger.debug("Skipping browser IP comparison for trusted Next.js SSR request")
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

    try:
        token_session_version = int(payload.get("sv", 0))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # The cache contains no password hash or OAuth secrets. Session-version
    # matching plus DB-authoritative security fields preserves revocation
    # semantics even if cache invalidation fails.  On a cache miss, the full
    # user query below is already authoritative, so avoid a duplicate state
    # query and save one database round trip.
    cached_user = await get_cached_auth_user(user_id, token_session_version)
    if cached_user is not None:
        try:
            authoritative_state = await _get_authoritative_auth_state(
                db, user_id, token_session_version
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Authoritative user state lookup failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        _apply_authoritative_auth_state(cached_user, authoritative_state)
        return cached_user

    # Database lookup on a cache miss
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
        await cache_auth_user(user)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database user lookup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )


async def get_current_user_optional(  # noqa: PLR0911
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

    try:
        token_session_version = int(payload.get("sv", 0))
    except (TypeError, ValueError):
        return None

    cached_user = await get_cached_auth_user(user_id, token_session_version)
    if cached_user is not None:
        try:
            authoritative_state = await _get_authoritative_auth_state(
                db, user_id, token_session_version
            )
        except Exception:
            return None
        _apply_authoritative_auth_state(cached_user, authoritative_state)
        return cached_user

    # Database lookup on a cache miss
    try:
        user = await user_service.get_user_by_id(user_id)
        if user is not None and not _session_version_matches(payload, user):
            return None
        if user is not None:
            await cache_auth_user(user)
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
