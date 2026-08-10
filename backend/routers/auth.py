"""
Authentication router for login, register, and token management.
Refactored for Async operations.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from dependencies import (
    get_current_active_user,
    get_password_reset_service,
    get_user_service,
)
from dependencies.auth import verify_token_fingerprint
from models.token_blacklist import TokenBlacklist
from models.user import User
from rate_limiter import auth_rate_limiter
from schemas.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from schemas.user import (
    GithubAuth,
    GoogleAuth,
    UserCreate,
    UserLogin,
    UserResponse,
)
from services.async_password_reset_service import AsyncPasswordResetService
from services.async_user_service import AsyncUserService
from utils.auth import (
    async_verify_token_with_blacklist,
    get_token_expiration,
)
from utils.github_oauth import (
    async_exchange_code_for_token,
    async_get_github_user_info,
    is_github_oauth_configured,
)
from utils.google_oauth import (
    async_verify_google_access_token,
    async_verify_google_id_token,
    is_google_oauth_configured,
)
from utils.logger import mask_email, mask_token, setup_logger
from utils.token_utils import (
    ACCESS_TOKEN_KEY,
    COOKIE_SECURE,
    REFRESH_TOKEN_KEY,
    clear_auth_cookies,
    create_and_set_auth_cookies,
)

logger = setup_logger("auth_router")

router = APIRouter(prefix="/auth", tags=["authentication"])


def _get_session_version(user: User) -> int:
    """Return a normalized session version for token issuance."""
    version = getattr(user, "session_version", 0)
    return version if isinstance(version, int) else 0


def _session_version_matches(payload: dict[str, Any], user: User) -> bool:
    """Reject refresh tokens issued before the user's current session version."""
    try:
        return int(payload.get("sv", 0)) == _get_session_version(user)
    except (TypeError, ValueError):
        return False


# Log cookie security setting
if not COOKIE_SECURE:
    logger.info("⚠️ COOKIE_SECURE is FALSE (Development Mode). Cookies will be accepted over HTTP.")
else:
    logger.info("🔒 COOKIE_SECURE is TRUE (Production Mode). HTTPS required for cookies.")


def _login_success_response(user: User, *, role: str | None = None) -> dict[str, Any]:
    return {
        "message": "Login successful",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "name": user.name,
            "firstName": getattr(user, "first_name", None),
            "lastName": getattr(user, "last_name", None),
            "avatar": user.avatar_url,
            "role": role or user.role,
            "isActive": user.is_active,
            "emailVerified": getattr(user, "is_verified", True),
        },
    }


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    user_service: AsyncUserService = Depends(get_user_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Register a new user and send verification email.
    """
    from security.password import validate_password

    # Check if user already exists
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Validate input
    if not user_data.password and not user_data.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either password or Google ID is required",
        )

    # Validate password strength using advanced password policy
    if user_data.password:
        user_context = {
            "email": user_data.email,
            "username": user_data.username,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
        }

        violations = await validate_password(user_data.password, user_context)

        if violations:
            # Collect error messages from violations
            error_messages = [v.message for v in violations]
            logger.warning(
                f"Password validation failed for {mask_email(user_data.email)}: "
                f"{len(violations)} violations"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet security requirements",
                    "violations": error_messages,
                },
            )

    try:
        user = await user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/verify-email")
async def verify_email(
    token: str,
    user_service: AsyncUserService = Depends(get_user_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Verify email address.
    """
    if await user_service.verify_email(token):
        return {"message": "Email verified successfully"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token"
    )


@router.post("/login", response_model=Any)
async def login(
    login_data: UserLogin,
    response: Response,
    request: Request,
    user_service: AsyncUserService = Depends(get_user_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Authenticate user and set access/refresh tokens as HttpOnly cookies.
    """
    logger.info(f"Login attempt for email: {mask_email(login_data.email)}")

    try:
        # Authenticate user with database
        # Get IP and UA for audit logs
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        try:
            user = await user_service.authenticate_user(login_data, ip_address, user_agent)
        except ValueError as ve:
            # Handle account lockout or other service errors
            if "Account locked" in str(ve):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ve))
            raise ve

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your email inbox.",
            )

        # Create and set auth tokens using centralized utility
        # A+ Security: Pass request for token fingerprinting (device binding)
        create_and_set_auth_cookies(
            response=response,
            user_id=str(user.id),
            log_user_info=mask_email(login_data.email),
            request=request,
            remember_me=login_data.remember_me,
            session_version=_get_session_version(user),
        )
        logger.debug(
            f"Cookie settings: secure={COOKIE_SECURE}, samesite='lax', httponly=True, path='/'"
        )

        # Prepare user info
        user_role = getattr(user, "role", None)
        if not user_role:
            user_role = "user"

        return _login_success_response(user, role=user_role)

    except HTTPException as http_err:
        logger.warning(f"Login rejected: {http_err.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login. Please try again.",
        )


@router.get("/me", response_model=UserResponse | None)
async def read_users_me(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.post("/google")
async def google_login(
    request: Request,
    response: Response,
    google_data: GoogleAuth,
    user_service: AsyncUserService = Depends(get_user_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Authenticate user with Google OAuth.
    """
    try:
        # Check if Google OAuth is configured
        if not is_google_oauth_configured():
            logger.error("Google OAuth is not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.",
            )

        # Verify Google token (ID token or Access token)
        google_user_info = None

        if google_data.id_token:
            google_user_info = await async_verify_google_id_token(google_data.id_token)
        elif google_data.access_token:
            google_user_info = await async_verify_google_access_token(google_data.access_token)

        if not google_user_info:
            logger.error("Failed to verify Google token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token"
            )

        # Check if email is verified
        if not google_user_info.get("email_verified", False):
            logger.error("Google email not verified")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email is not verified"
            )

        # Create or update user from Google authentication
        user = await user_service.create_or_update_google_user(
            google_id=google_user_info["id"],
            email=google_user_info["email"],
            name=google_user_info["name"],
            avatar_url=google_user_info.get("picture"),
        )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

        # Update last login time
        await user_service.update_last_login(user.id)

        # Create and set auth tokens using centralized utility
        # A+ Security: Pass request for token fingerprinting (device binding)
        create_and_set_auth_cookies(
            response=response,
            user_id=str(user.id),
            log_user_info=mask_email(user.email),
            request=request,
            session_version=_get_session_version(user),
        )

        return _login_success_response(user)

    except HTTPException as http_err:
        logger.error(f"HTTP error during Google login: {http_err.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during Google login: {e!s}")
        raise


@router.post("/github")
async def github_login(
    request: Request,
    response: Response,
    github_data: GithubAuth,
    user_service: AsyncUserService = Depends(get_user_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Authenticate user with GitHub OAuth.
    """
    try:
        # Check if GitHub OAuth is configured
        if not is_github_oauth_configured():
            logger.error("GitHub OAuth is not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables.",
            )

        # Get access token (either from code exchange or directly)
        access_token = None

        if github_data.code:
            # Exchange authorization code for access token (using async version for non-blocking I/O)
            access_token = await async_exchange_code_for_token(
                github_data.code, github_data.redirect_uri
            )
        elif github_data.access_token:
            # Use provided access token directly
            access_token = github_data.access_token

        if not access_token:
            logger.error("Failed to obtain GitHub access token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to authenticate with GitHub",
            )

        # Get user info from GitHub (using async version for non-blocking I/O)
        github_user_info = await async_get_github_user_info(access_token)

        if not github_user_info:
            logger.error("Failed to get GitHub user info")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get user information from GitHub",
            )

        # Create or update user from GitHub authentication
        user = await user_service.create_or_update_github_user(
            github_id=github_user_info["id"],
            email=github_user_info["email"],
            name=github_user_info["name"],
            avatar_url=github_user_info.get("picture"),
        )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

        # Update last login time
        await user_service.update_last_login(user.id)

        # Create and set auth tokens using centralized utility
        # A+ Security: Pass request for token fingerprinting (device binding)
        create_and_set_auth_cookies(
            response=response,
            user_id=str(user.id),
            log_user_info=mask_email(user.email),
            request=request,
            session_version=_get_session_version(user),
        )

        return _login_success_response(user)

    except HTTPException as http_err:
        logger.error(f"HTTP error during GitHub login: {http_err.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during GitHub login: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during GitHub authentication",
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Logout user, clear cookies, and blacklist the current access token.
    Always returns success to ensure cookies are cleared on the client.
    """
    user_email = "unknown"
    try:
        # Clear cookies using centralized utility
        # This is the most important part - it must run regardless of token validity
        clear_auth_cookies(response)

        tokens: list[tuple[str | None, Literal["access", "refresh"]]] = [
            (request.cookies.get(ACCESS_TOKEN_KEY), "access"),
            (request.cookies.get(REFRESH_TOKEN_KEY), "refresh"),
        ]
        if not tokens[0][0]:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                tokens[0] = (auth_header.split(" ", 1)[1], "access")

        # Blacklist both cookies so logout also invalidates refresh rotation.
        from utils.auth import verify_token

        for token, token_type in tokens:
            if not token:
                continue
            try:
                payload = verify_token(token, expected_type=token_type)
                user_email = payload.get("sub", "unknown")
                token_jti = payload.get("jti")
                token_expiration = get_token_expiration(token)
                if token_jti and token_expiration:
                    await TokenBlacklist.async_blacklist_token(db, token_jti, token_expiration)
            except Exception:
                # Expired or invalid tokens need no further logout action.
                pass

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Error during logout for user {mask_email(user_email)}: {e}")
        # Still return success even if blacklisting fails
        return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Any)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    user_service: AsyncUserService = Depends(get_user_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Refresh access token using a refresh token from HttpOnly cookie.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get(REFRESH_TOKEN_KEY)

    # Fallback/Debug: check header
    if not refresh_token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header.split(" ")[1]

    if not refresh_token:
        logger.error("Refresh token is null or empty")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is null or empty",
        )

    try:
        # Verify refresh token with blacklist checking (Async)
        payload = await async_verify_token_with_blacklist(
            refresh_token, db, expected_type="refresh"
        )

        # Extract user_id from payload
        user_id = payload.get("sub")

        token_jti = payload.get("jti")

        if user_id is None:
            logger.error("No user ID found in refresh token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except HTTPException:
        # Re-raise HTTP exceptions (like Token has been revoked) without logging as error
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Get user from database
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        logger.error(f"User not found for ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    await verify_token_fingerprint(request, payload, str(user.id), db)

    if not _session_version_matches(payload, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalid - please login again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"User {user_id} is not active")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    # Capture scalar auth state before token-rotation writes.  A concurrent
    # duplicate JTI claim rolls the SQLAlchemy session back; rollback expires
    # ORM attributes, and reading ``user`` afterwards would trigger an async
    # lazy refresh from synchronous response code (MissingGreenlet).
    refresh_user_id = str(user.id)
    refresh_session_version = _get_session_version(user)

    # Blacklist the old refresh token (rotation)
    if token_jti:
        old_token_expiration = get_token_expiration(refresh_token)
        if old_token_expiration:
            claimed = await TokenBlacklist.async_blacklist_token(
                db, token_jti, old_token_expiration
            )
            if not claimed:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has already been used",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    # Create and set new tokens using centralized utility
    # A+ Security: Pass request for token fingerprinting (device binding)
    create_and_set_auth_cookies(
        response=response,
        user_id=refresh_user_id,
        request=request,
        session_version=refresh_session_version,
    )

    return {"message": "Token refreshed successfully", "expires_in": 1800}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    password_reset_service: AsyncPasswordResetService = Depends(get_password_reset_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Send password reset email to user.
    """
    try:
        # Create reset token
        reset_token = await password_reset_service.create_password_reset_token(request_data.email)

        if not reset_token:
            # Don't reveal if email exists or not for security
            logger.info(
                f"Password reset requested for non-existent email: {mask_email(request_data.email)}"
            )
            return ForgotPasswordResponse(
                message="If your email is registered, you will receive a password reset link shortly.",
                success=True,
            )

        # Token creation atomically persisted the durable email job. Avoid a
        # second enqueue/commit round trip for the same reset request.
        logger.info(f"Password reset email queued for: {mask_email(request_data.email)}")
        return ForgotPasswordResponse(
            message="If your email is registered, you will receive a password reset link shortly.",
            success=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in forgot password for email {mask_email(request_data.email)}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request_data: ResetPasswordRequest,
    password_reset_service: AsyncPasswordResetService = Depends(get_password_reset_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Reset user's password using a valid token.
    """
    from security.password import validate_password

    try:
        # Validate new password strength
        violations = await validate_password(request_data.new_password)
        if violations:
            error_messages = [v.message for v in violations]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet security requirements",
                    "violations": error_messages,
                },
            )

        # Validate token and reset password
        success = await password_reset_service.reset_password(
            request_data.token, request_data.new_password
        )

        if success:
            logger.info(f"Password reset successful for token: {mask_token(request_data.token)}")
            return ResetPasswordResponse(
                message="Password has been reset successfully. You can now login with your new password.",
                success=True,
            )
        else:
            logger.warning(f"Password reset failed for token: {mask_token(request_data.token)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reset password for token {mask_token(request_data.token)}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=128, alias="currentPassword")
    new_password: str = Field(..., min_length=8, max_length=128, alias="newPassword")


class ValidateResetTokenRequest(BaseModel):
    token: str = Field(..., max_length=512)


class ValidateResetTokenResponse(BaseModel):
    valid: bool
    message: str | None = None


@router.post("/validate-reset-token", response_model=ValidateResetTokenResponse)
async def validate_reset_token(
    request_data: ValidateResetTokenRequest,
    password_reset_service: AsyncPasswordResetService = Depends(get_password_reset_service),
    _=Depends(auth_rate_limiter),
) -> Any:
    """
    Validate a password reset token.
    """
    try:
        # Validate token
        reset_token = await password_reset_service.validate_reset_token(request_data.token)

        if reset_token:
            logger.info(
                f"Reset token validation successful for token: {mask_token(request_data.token)}"
            )
            return ValidateResetTokenResponse(valid=True, message="Token is valid")
        else:
            logger.warning(
                f"Reset token validation failed for token: {mask_token(request_data.token)}"
            )
            return ValidateResetTokenResponse(valid=False, message="Invalid or expired reset token")

    except Exception as e:
        logger.error(f"Error validating reset token: {e}")
        return ValidateResetTokenResponse(valid=False, message="Failed to validate reset token")


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    user_service: AsyncUserService = Depends(get_user_service),
) -> Any:
    """
    Change current user's password.
    """
    from security.password import validate_password

    try:
        logger.info(f"Password change attempt for user: {mask_email(current_user.email)}")

        # Cached auth snapshots intentionally omit password hashes. Sensitive
        # password verification remains database-backed on this endpoint.
        password_user: User | None = current_user
        if not getattr(password_user, "hashed_password", None):
            password_user = await user_service.get_user_by_id(current_user.id)

        if (
            not password_user
            or not password_user.hashed_password
            or not await user_service.verify_password(
                password_data.current_password, password_user.hashed_password
            )
        ):
            logger.warning(
                f"Current password verification failed for user: {mask_email(current_user.email)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
            )

        # Validate new password strength
        user_context = {
            "email": current_user.email,
            "username": current_user.username,
            "first_name": getattr(current_user, "first_name", None),
            "last_name": getattr(current_user, "last_name", None),
        }
        violations = await validate_password(password_data.new_password, user_context)
        if violations:
            error_messages = [v.message for v in violations]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet security requirements",
                    "violations": error_messages,
                },
            )

        await user_service.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password,
            verified_user=password_user,
            current_password_verified=True,
        )
        logger.info(f"Password changed successfully for user: {mask_email(current_user.email)}")
        return {"message": "Password changed successfully"}
    except ValueError as e:
        logger.error(
            f"Validation error changing password for user {mask_email(current_user.email)}: {e}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error changing password for user {mask_email(current_user.email)}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to change password"
        )
