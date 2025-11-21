"""
Authentication router for login, register, and token management.
"""
from datetime import timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserLogin, UserResponse, Token, GoogleAuth
from models.user import User
from services.user_service import UserService
from utils.auth import create_access_token, verify_token
from database import get_db
from utils.logger import setup_logger
import uuid

logger = setup_logger("auth_router")

router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth2 scheme for token authentication
# Set auto_error=False so we can fallback to cookie-based tokens when Authorization header is absent
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=True)

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Any:
    """Get current authenticated user from token (Authorization: Bearer ...)."""
    # The token is extracted by OAuth2PasswordBearer from Authorization header
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No token provided",
            )

        payload = verify_token(token)
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
            logger.warning(f"User not found in database: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        logger.info(f"Successfully authenticated user: {user.email} (ID: {user.id})")
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
        logger.debug(f"Called for user: {user_email} (ID: {user_id})")
    else:
        user_email = getattr(current_user, 'email', 'unknown')
        user_id = getattr(current_user, 'id', 'unknown')
        is_active = getattr(current_user, 'is_active', True)
        logger.debug(f"Called for user: {user_email} (ID: {user_id})")
    
    if not is_active:
        logger.warning(f"User {user_email} is not active")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    logger.debug(f"User {current_user.email} is active")
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

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, response: Response, db: Session = Depends(get_db)) -> Any:
    """
    Authenticate user and return access token using database authentication.
    """
    logger.info(f"Login attempt for email: {login_data.email}")
    logger.info(f"Login attempt - Password provided: {'YES' if login_data.password else 'NO'}")
    logger.info(f"Login attempt - Password length: {len(login_data.password) if login_data.password else 0}")
    
    try:
        # Use real database authentication
        user_service = UserService(db)
        logger.info(f"Using database authentication for: {login_data.email}")
        
        # Authenticate user with database
        user = user_service.authenticate_user(login_data)
        
        if not user:
            logger.warning(f"Authentication failed for email: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"User {login_data.email} is not active")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        logger.info(f"User {login_data.email} authenticated successfully, user_id: {user.id}")
        
        # Create tokens for authenticated user
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Create refresh token with longer expiration
        refresh_token_expires = timedelta(days=7)
        refresh_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=refresh_token_expires
        )
        
        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800  # 30 minutes in seconds
        }

        logger.info(f"Tokens created successfully for user {login_data.email}")
        logger.info(f"Access token length: {len(access_token) if access_token else 0}")
        logger.info(f"Refresh token length: {len(refresh_token) if refresh_token else 0}")

        # Prepare response data - include user object for frontend compatibility
        user_role = getattr(user, 'role', None)
        if not user_role:
            user_role = 'user'  # Default role for existing users without role field
        
        response_data = {
            **tokens,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user_role,
                "is_active": user.is_active
            }
        }
        
        logger.info(f"Returning response data keys: {list(response_data.keys())}")
        logger.info(f"Response includes user object: {bool(response_data.get('user'))}")

        # Return tokens in body (Bearer token flow)
        return response_data
        
    except HTTPException as http_err:
        logger.error(f"HTTP error during login for email {login_data.email}: {http_err.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login for email {login_data.email}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    Get current user information.
    """
    return current_user

@router.post("/google")
def google_login(google_data: GoogleAuth, db: Session = Depends(get_db)) -> Any:
    """
    Authenticate user with Google OAuth.
    """
    try:
        user_service = UserService(db)
        
        # In a real implementation, you would verify Google ID token
        # For now, we'll simulate it with a mock implementation
        # Extract user info from Google token (mock implementation)
        mock_google_user_info = {
            "id": "mock-google-id",
            "email": "user@gmail.com",
            "name": "Google User",
            "picture": "https://lh3.googleusercontent.com/a/default-user"
        }
        
        # Create or update user from Google authentication
        user = user_service.create_or_update_google_user(
            google_id=mock_google_user_info["id"],
            email=mock_google_user_info["email"],
            name=mock_google_user_info["name"],
            avatar_url=mock_google_user_info["picture"]
        )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Create refresh token with longer expiration
        refresh_token_expires = timedelta(days=7)
        refresh_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800  # 30 minutes in seconds
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in Google login: {e}")
        logger.error(f"Full traceback: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during Google authentication: {str(e)}"
        )

@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    Logout user.
    """
    # In a stateless JWT implementation, we don't need to do anything on server side
    # The client will simply discard tokens
    # In a more complex implementation, we might want to add token to a blacklist
    # Clear cookies by setting empty values and immediate expiry
    # Client-side should discard tokens; server can optionally handle revocation if implemented
    return {"message": "Successfully logged out"}

@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
) -> Any:
    """
    Refresh access token using a refresh token.
    """
    # Expect refresh token via Authorization header: Bearer <refresh_token>
    auth_header = request.headers.get("authorization")
    logger.debug(f"Refresh token request - Authorization header: {auth_header}")
    refresh_token = None
    if auth_header and auth_header.startswith("Bearer "):
        refresh_token = auth_header.split(" ")[1]

    logger.debug(f"Refresh token extracted: {refresh_token[:20] if refresh_token else 'NO_TOKEN'}")
    if not refresh_token:
        logger.error("Refresh token is null or empty")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is null or empty",
        )
    
    try:
        # Verify refresh token
        payload = verify_token(refresh_token)
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.error("No user ID found in refresh token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        logger.debug(f"Refresh token verified successfully for user_id: {user_id}")
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
    
    # Create new access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # Create new refresh token
    refresh_token_expires = timedelta(days=7)
    new_refresh_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires
    )
    # Set new cookies for refreshed tokens
    import os
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    secure_flag = not debug_mode
    same_site = 'None' if not debug_mode else 'Lax'

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure_flag,
        samesite=same_site,
        max_age=1800,
        path='/'
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=secure_flag,
        samesite=same_site,
        max_age=7 * 24 * 3600,
        path='/'
    )
    
    logger.info(f"Tokens refreshed successfully for user: {user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 1800  # 30 minutes in seconds
    }