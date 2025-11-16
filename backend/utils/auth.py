"""
Authentication utilities for JWT token handling and password management.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import os
import json
import time
from dotenv import load_dotenv
from utils.logger import setup_logger

logger = setup_logger("auth_utils")

# Load environment variables
load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Log environment information using proper logger
logger.debug(f"SECRET_KEY loaded: {'YES' if SECRET_KEY and SECRET_KEY != 'your-secret-key-here-change-in-production' else 'NO'}")
logger.debug(f"SECRET_KEY length: {len(SECRET_KEY) if SECRET_KEY else 0}")

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    """
    
    try:
        logger.debug(f"Attempting to decode token: {token[:20]}...")
        logger.debug(f"Using SECRET_KEY: {SECRET_KEY[:10]}... (length: {len(SECRET_KEY)})")
        logger.debug(f"Using ALGORITHM: {ALGORITHM}")
        logger.debug(f"Token structure check - has 3 parts: {token.count('.') == 3}")
        
        # Check token structure
        token_parts = token.split('.')
        if len(token_parts) != 3:
            logger.warning(f"Invalid token structure - expected 3 parts, got {len(token_parts)}")
            raise ValueError("Invalid token structure")
            
        # Try to decode payload for additional debugging
        try:
            import base64
            # Add padding if needed
            payload_b64 = token_parts[1]
            # Calculate required padding
            padding_needed = 4 - (len(payload_b64) % 4)
            if padding_needed and padding_needed != 4:
                payload_b64 += '=' * padding_needed
            payload_json = base64.b64decode(payload_b64)
            payload_data = json.loads(payload_json)
            logger.debug(f"Token payload preview: {payload_data}")
            
            # Check expiration with timezone awareness
            import time
            current_time = int(time.time())
            exp_time = payload_data.get('exp')
            if exp_time:
                logger.debug(f"Token expiration - current: {current_time}, exp: {exp_time}, time_until_expiry: {exp_time - current_time}")
                if exp_time < current_time:
                    logger.warning(f"Token has expired! Current time: {datetime.fromtimestamp(current_time, tz=timezone.utc)}, Exp: {datetime.fromtimestamp(exp_time, tz=timezone.utc)}")
                    raise ValueError("Token has expired")
        except Exception as payload_error:
            logger.warning(f"Could not decode token payload for debugging: {payload_error}")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Successfully decoded payload: {payload}")
        return payload
    except JWTError as e:
        logger.error(f"JWTError occurred: {e}")
        logger.error(f"SECRET_KEY being used: {SECRET_KEY[:10]}... (length: {len(SECRET_KEY)})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"SECRET_KEY being used: {SECRET_KEY[:10]}... (length: {len(SECRET_KEY)})")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
def authenticate_user(user, password: str) -> bool:
    """
    Authenticate a user by verifying their password.
    """
    logger.debug(f"authenticate_user called for user_id: {user.id if user else 'None'}")
    logger.debug(f"Password provided: {'YES' if password else 'NO'}")
    
    if not user:
        logger.warning("User object is None in authenticate_user")
        return False
        
    if not user.hashed_password:
        logger.warning(f"User {user.id} has no hashed_password")
        return False
    
    logger.debug(f"Attempting to verify password for user {user.id}")
    try:
        result = verify_password(password, user.hashed_password)
        logger.debug(f"Password verification result for user {user.id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error during password verification for user {user.id}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False
def authenticate_user(user, password: str) -> bool:
    """
    Authenticate a user by verifying their password.
    """
    if not user or not user.hashed_password:
        return False
    return verify_password(password, user.hashed_password)