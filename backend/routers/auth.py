"""
Authentication router for login, register, and token management.
"""
from datetime import timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserLogin, UserResponse, Token, GoogleAuth
from schemas.password_reset import ForgotPasswordRequest, ForgotPasswordResponse, ResetPasswordRequest, ResetPasswordResponse
from pydantic import BaseModel, Field
from models.user import User
from models.token_blacklist import TokenBlacklist
from services.user_service import UserService
from services.password_reset_service import PasswordResetService

from utils.auth import create_access_token, verify_token_with_blacklist, get_token_expiration
from utils.google_oauth import verify_google_id_token, verify_google_access_token, is_google_oauth_configured
from utils.rate_limiter import auth_rate_limiter
from database import get_db
from utils.logger import setup_logger
import uuid
import os 

logger = setup_logger("auth_router")

router = APIRouter(prefix="/auth", tags=["authentication"])

# Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
ACCESS_TOKEN_KEY = "access_token"
REFRESH_TOKEN_KEY = "refresh_token"
# Set secure=True in production, False in development
# IMPORTANT: For localhost development (HTTP), this MUST be False.
COOKIE_SECURE = os.getenv("ENVIRONMENT") == "production"
if not COOKIE_SECURE:
    logger.info("⚠️ COOKIE_SECURE is FALSE (Development Mode). Cookies will be accepted over HTTP.")
else:
    logger.info("🔒 COOKIE_SECURE is TRUE (Production Mode). HTTPS required for cookies.") 


# OAuth2 scheme for token authentication
# Set auto_error=False so we can fallback to cookie-based tokens when Authorization header is absent
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)



def get_token_from_cookie_or_header(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[str]:
    """Get token from Authorization header or HttpOnly cookie."""
    if token:
        return token
    
    # Fallback to manual header check if OAuth2 scheme didn't catch it (e.g. Bearer with lowercase b or other issues)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    return request.cookies.get(ACCESS_TOKEN_KEY)

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_token_from_cookie_or_header)
) -> Any:
    """Get current authenticated user from token (Cookie or Header)."""
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated - No token provided",
            )

        # Verify token with blacklist checking
        payload = verify_token_with_blacklist(token, db)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # Database lookup only (removed mock authentication)
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Database user lookup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    # Handle both dict (mock user) and object (database user)
    if isinstance(current_user, dict):
        user_email = current_user.get('email', 'unknown')
        user_id = current_user.get('id', 'unknown')
        is_active = current_user.get('is_active', True)
    else:
        user_email = getattr(current_user, 'email', 'unknown')
        user_id = getattr(current_user, 'id', 'unknown')
        is_active = getattr(current_user, 'is_active', True)
    
    if not is_active:
        logger.warning(f"User {user_email} is not active")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Register a new user.
    """
    user_service = UserService(db)
    
    # Check if user already exists
    existing_user = user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate input
    if not user_data.password and not user_data.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either password or Google ID is required"
        )
    
    try:
        user = user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Any)
def login(
    login_data: UserLogin, 
    response: Response, 
    db: Session = Depends(get_db),
    _ = Depends(auth_rate_limiter)
) -> Any:
    """
    Authenticate user and set access/refresh tokens as HttpOnly cookies.
    """
    logger.info(f"Login attempt for email: {login_data.email}")    # Removed sensitive password logging
    
    try:
        # Use real database authentication
        user_service = UserService(db)
        
        # Authenticate user with database
        user = user_service.authenticate_user(login_data)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Create tokens for authenticated user
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Create refresh token with longer expiration
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=refresh_token_expires
        )
        
        # Set HttpOnly cookies
        response.set_cookie(
            key=ACCESS_TOKEN_KEY,
            value=access_token,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            path="/"
        )
        
        response.set_cookie(
            key=REFRESH_TOKEN_KEY,
            value=refresh_token,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/"
        )

        logger.info(f"Tokens set as HttpOnly cookies for user {login_data.email}")
        logger.info(f"Cookie settings: secure={COOKIE_SECURE}, samesite='lax', httponly=True, path='/'")
        
        # Prepare user info
        user_role = getattr(user, 'role', None)
        if not user_role:
            user_role = 'user'

        # Return user info without tokens in body
        return {
            "message": "Login successful",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user_role,
                "is_active": user.is_active
            }
        }
        
    except HTTPException as http_err:
        logger.error(f"HTTP error during login: {http_err.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    Get current user information.
    """
    return current_user

@router.post("/google")
def google_login(response: Response, google_data: GoogleAuth, db: Session = Depends(get_db)) -> Any:
    """
    Authenticate user with Google OAuth.
    """
    try:
        # Check if Google OAuth is configured
        if not is_google_oauth_configured():
            logger.error("Google OAuth is not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
            )
        
        # Verify Google token (ID token or Access token)
        google_user_info = None
        
        if google_data.id_token:
            google_user_info = verify_google_id_token(google_data.id_token)
        elif google_data.access_token:
            google_user_info = verify_google_access_token(google_data.access_token)
            
        if not google_user_info:
            logger.error("Failed to verify Google token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
        
        # Check if email is verified
        if not google_user_info.get("email_verified", False):
            logger.error(f"Google email not verified")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is not verified"
            )
        
        # Create or update user from Google authentication
        user_service = UserService(db)
        user = user_service.create_or_update_google_user(
            google_id=google_user_info["id"],
            email=google_user_info["email"],
            name=google_user_info["name"],
            avatar_url=google_user_info.get("picture")
        )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Create refresh token with longer expiration
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=refresh_token_expires
        )
        
        # Set HttpOnly cookies
        response.set_cookie(
            key=ACCESS_TOKEN_KEY,
            value=access_token,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )
        
        response.set_cookie(
            key=REFRESH_TOKEN_KEY,
            value=refresh_token,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/"
        )
        
        return {
            "message": "Login successful",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "is_active": user.is_active
            }
        }
        
    except HTTPException as http_err:
        logger.error(f"HTTP error during Google login: {http_err.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during Google login: {str(e)}")
        raise
        

        



@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Logout user, clear cookies, and blacklist the current access token.
    """
    try:
        # Clear cookies
        response.delete_cookie(ACCESS_TOKEN_KEY)
        response.delete_cookie(REFRESH_TOKEN_KEY)
        
        # Get token from cookie or header
        token = request.cookies.get(ACCESS_TOKEN_KEY)
        if not token:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if token:
            
            # Get token payload to extract jti and expiration
            from utils.auth import verify_token
            payload = verify_token(token)
            token_jti = payload.get('jti')
            
            if token_jti:
                # Get token expiration
                token_expiration = get_token_expiration(token)
                if token_expiration:
                    # Add token to blacklist
                    TokenBlacklist.blacklist_token(db, token_jti, token_expiration)
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Error during logout for user {current_user.email}: {e}")
        # Still return success even if blacklisting fails
        return {"message": "Successfully logged out"}

@router.post("/refresh", response_model=Any)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
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
        # Verify refresh token with blacklist checking
        from utils.auth import verify_token
        payload = verify_token(refresh_token)
        
        # Extract user_id from payload
        user_id = payload.get("sub")
        
        # Check if refresh token is blacklisted
        token_jti = payload.get('jti')
        if token_jti and TokenBlacklist.is_token_blacklisted(db, token_jti):
            logger.warning(f"Refresh token {token_jti} is blacklisted")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )
        
        if user_id is None:
            logger.error("No user ID found in refresh token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Get user from database
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    if user is None:
        logger.error(f"User not found for ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        logger.warning(f"User {user_id} is not active")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Blacklist the old refresh token (rotation)
    if token_jti:
        old_token_expiration = get_token_expiration(refresh_token)
        if old_token_expiration:
            TokenBlacklist.blacklist_token(db, token_jti, old_token_expiration)
    
    # Create new access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # Create new refresh token (rotation)
    refresh_token_expires = timedelta(days=7)
    new_refresh_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires
    )
    

    # Set HttpOnly cookies
    response.set_cookie(
        key=ACCESS_TOKEN_KEY,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/"
    )
    
    response.set_cookie(
        key=REFRESH_TOKEN_KEY,
        value=new_refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/"
    )

    return {
        "message": "Token refreshed successfully",
        "expires_in": 1800
    }

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    request_data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    _ = Depends(auth_rate_limiter)
) -> Any:
    """
    Send password reset email to user.
    """
    try:
        password_reset_service = PasswordResetService(db)
        
        # Create reset token
        reset_token = password_reset_service.create_password_reset_token(request_data.email)
        
        if not reset_token:
            # Don't reveal if email exists or not for security
            logger.info(f"Password reset requested for non-existent email: {request_data.email}")
            return ForgotPasswordResponse(
                message="If your email is registered, you will receive a password reset link shortly.",
                success=True
            )
        
        # Send reset email
        # Use raw_token if available (it was attached in create_password_reset_token)
        token_to_send = getattr(reset_token, 'raw_token', reset_token.token)
        email_sent = password_reset_service.send_reset_email(request_data.email, token_to_send)
        
        if email_sent:
            logger.info(f"Password reset email sent to: {request_data.email}")
            return ForgotPasswordResponse(
                message="If your email is registered, you will receive a password reset link shortly.",
                success=True
            )
        else:
            logger.error(f"Failed to send password reset email to: {request_data.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in forgot password for email {request_data.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    request_data: ResetPasswordRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Reset user's password using a valid token.
    """
    try:
        password_reset_service = PasswordResetService(db)
        
        # Validate token and reset password
        success = password_reset_service.reset_password(request_data.token, request_data.new_password)
        
        if success:
            logger.info(f"Password reset successful for token: {request_data.token}")
            return ResetPasswordResponse(
                message="Password has been reset successfully. You can now login with your new password.",
                success=True
            )
        else:
            logger.warning(f"Password reset failed for token: {request_data.token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reset password for token {request_data.token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., alias="currentPassword")
    new_password: str = Field(..., alias="newPassword")

class ValidateResetTokenRequest(BaseModel):
    token: str

class ValidateResetTokenResponse(BaseModel):
    valid: bool
    message: Optional[str] = None

@router.post("/validate-reset-token", response_model=ValidateResetTokenResponse)
def validate_reset_token(
    request_data: ValidateResetTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Validate a password reset token.
    """
    try:
        password_reset_service = PasswordResetService(db)
        
        # Validate token
        reset_token = password_reset_service.validate_reset_token(request_data.token)
        
        if reset_token:
            logger.info(f"Reset token validation successful for token: {request_data.token[:10]}...")
            return ValidateResetTokenResponse(
                valid=True,
                message="Token is valid"
            )
        else:
            logger.warning(f"Reset token validation failed for token: {request_data.token[:10]}...")
            return ValidateResetTokenResponse(
                valid=False,
                message="Invalid or expired reset token"
            )
            
    except Exception as e:
        logger.error(f"Error validating reset token: {e}")
        return ValidateResetTokenResponse(
            valid=False,
            message="Failed to validate reset token"
        )

@router.post("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Change current user's password.
    """
    user_service = UserService(db)
    
    try:
        logger.info(f"Password change attempt for user: {current_user.email}")
        
        # Verify current password before changing
        if not user_service.verify_password(password_data.current_password, current_user.hashed_password):
            logger.warning(f"Current password verification failed for user: {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        user_service.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password
        )
        logger.info(f"Password changed successfully for user: {current_user.email}")
        return {"message": "Password changed successfully"}
    except ValueError as e:
        logger.error(f"Validation error changing password for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error changing password for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )