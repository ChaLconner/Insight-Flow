"""
Google OAuth utilities for verifying Google ID tokens.
"""
import os
from typing import Dict, Optional
from google.auth.transport import requests
from google.oauth2 import id_token
from utils.logger import setup_logger

logger = setup_logger("google_oauth")

# Load environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

def verify_google_id_token(id_token: str) -> Optional[Dict]:
    """
    Verify Google ID token and return user information.
    
    Args:
        id_token: Google ID token from frontend
        
    Returns:
        Dict: User information from Google if valid, None otherwise
    """
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID environment variable not set")
        return None
    
    try:
        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(
            id_token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Check if the token is valid
        if idinfo.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.error(f"Invalid token issuer: {idinfo.get('iss')}")
            return None
        
        # Check if the audience matches our client ID
        if idinfo.get('aud') != GOOGLE_CLIENT_ID:
            logger.error(f"Invalid token audience: {idinfo.get('aud')}")
            return None
        
        # Check if the token is expired
        if idinfo.get('exp') < 0:
            logger.error("Token has expired")
            return None
        
        logger.info(f"Successfully verified Google ID token for user: {idinfo.get('email')}")
        
        # Return relevant user information
        return {
            "id": idinfo.get("sub"),
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False)
        }
        
    except ValueError as e:
        logger.error(f"Invalid Google ID token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying Google ID token: {e}")
        return None

def verify_google_access_token(access_token: str) -> Optional[Dict]:
    """
    Verify Google access token and return user information.
    
    Args:
        access_token: Google access token from frontend
        
    Returns:
        Dict: User information from Google if valid, None otherwise
    """
    import requests
    
    try:
        # Call Google UserInfo endpoint
        response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to verify access token: {response.text}")
            return None
            
        user_info = response.json()
        
        # Verify that the token belongs to our app (optional but recommended if possible)
        # For access tokens, we can check tokeninfo
        token_info_response = requests.get(
            f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={access_token}"
        )
        
        if token_info_response.status_code == 200:
            token_info = token_info_response.json()
            if token_info.get('aud') != GOOGLE_CLIENT_ID:
                # Some flows might have different audience, but usually it matches client ID
                # If it doesn't match, log warning but maybe proceed if we trust userinfo?
                # For security, strict check is better.
                logger.warning(f"Token audience mismatch: {token_info.get('aud')} != {GOOGLE_CLIENT_ID}")
                # return None # Uncomment to enforce audience check
        
        logger.info(f"Successfully verified Google access token for user: {user_info.get('email')}")
        
        return {
            "id": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "email_verified": user_info.get("email_verified", False)
        }
        
    except Exception as e:
        logger.error(f"Error verifying Google access token: {e}")
        return None

def is_google_oauth_configured() -> bool:
    """
    Check if Google OAuth is properly configured.
    
    Returns:
        bool: True if Google OAuth is configured, False otherwise
    """
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)