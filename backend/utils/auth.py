"""
Authentication utilities for JWT token handling and password management.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import os
import json
import time
import uuid
from dotenv import load_dotenv
from utils.logger import setup_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = setup_logger("auth_utils")

# Load environment variables
load_dotenv()

# JWT Configuration
# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required for security. Please set it in your .env file.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))



# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password.
    """
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with JWT ID (jti) for blacklist functionality.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Add JWT ID (jti) for blacklist functionality
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": int(expire.timestamp()),
        "jti": jti,
        "iat": int(datetime.now(timezone.utc).timestamp())
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    """
    
    try:
        if not token:
            raise ValueError("Token is empty or None")
        
        # Check token structure
        token_parts = token.split('.')
        if len(token_parts) != 3:
            raise ValueError("Invalid token structure")
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_token_with_blacklist(token: str, db_session: "Session") -> Dict[str, Any]:
    """
    Verify and decode a JWT token, checking if it's blacklisted.
    
    Args:
        token: JWT token to verify
        db_session: Database session for blacklist checking
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or blacklisted
    """
    # First verify the token normally
    payload = verify_token(token)
    
    # Check if token is blacklisted
    from models.token_blacklist import TokenBlacklist
    token_jti = payload.get('jti')
    
    if token_jti and TokenBlacklist.is_token_blacklisted(db_session, token_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Extract expiration time from a JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        datetime: Expiration time of the token, or None if cannot be extracted
    """
    try:
        token_parts = token.split('.')
        if len(token_parts) != 3:
            return None
            
        # Decode payload
        import base64
        payload_b64 = token_parts[1]
        padding_needed = 4 - (len(payload_b64) % 4)
        if padding_needed and padding_needed != 4:
            payload_b64 += '=' * padding_needed
        payload_json = base64.b64decode(payload_b64)
        payload_data = json.loads(payload_json)
        
        exp_timestamp = payload_data.get('exp')
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
    except Exception as e:
        pass
    return None

def authenticate_user(user: Any, password: str) -> bool:
    """
    Authenticate a user by verifying their password.
    """
    if not user:
        return False
        
    if not user.hashed_password:
        return False
    
    try:
        result = verify_password(password, user.hashed_password)
        return result
    except Exception as e:
        return False