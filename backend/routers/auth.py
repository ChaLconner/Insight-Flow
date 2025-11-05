"""
Authentication router for login, register, and token management.
"""
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserLogin, UserResponse, Token, GoogleAuth
from models.user import User
from services.user_service import UserService
from utils.auth import create_access_token, verify_token
from database import get_db
import uuid

router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current authenticated user from token."""
    # The token is automatically extracted by OAuth2PasswordBearer
    print(f"Received access token: {token[:20]}...")  # Log first 20 chars for debugging
    
    try:
        print("Starting token verification...")
        payload = verify_token(token)
        print(f"Token verification successful, payload: {payload}")
        user_id: str = payload.get("sub")
        if user_id is None:
            print("No user ID found in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        print(f"Found user ID: {user_id}")
    except Exception as e:
        print(f"Token verification error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user_service = UserService(db)
    user = user_service.get_user_by_id(uuid.UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
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

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)) -> Any:
    """
    Authenticate user and return access token.
    """
    user_service = UserService(db)
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
        print(f"Error in Google login: {e}")
        print(f"Full traceback: {error_details}")
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
    return {"message": "Successfully logged out"}

@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Refresh access token using a refresh token.
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    
    refresh_token = auth_header.split(" ")[1]
    try:
        # Verify refresh token
        payload = verify_token(refresh_token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except Exception as e:
        print(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Get user from database
    user_service = UserService(db)
    user = user_service.get_user_by_id(uuid.UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
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
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 1800  # 30 minutes in seconds
    }