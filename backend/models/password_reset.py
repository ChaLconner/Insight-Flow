"""
Password reset model for Insight-Flow application.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, String, DateTime, Boolean
from .base import BaseModel
import secrets

class PasswordReset(BaseModel):
    """
    Password reset model for handling password reset tokens.
    """
    __tablename__ = "password_resets"
    
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    
    @staticmethod
    def generate_token():
        """Generate a secure random token for password reset."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash the token using SHA256."""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def create_reset_token(email: str, expires_hours: int = 1):
        """Create a password reset token with expiration."""
        raw_token = PasswordReset.generate_token()
        hashed_token = PasswordReset.hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
        
        reset_token = PasswordReset(
            email=email,
            token=hashed_token,
            expires_at=expires_at
        )
        return reset_token, raw_token
    
    def is_expired(self):
        """Check if the token has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self):
        """Check if the token is valid (not expired and not used)."""
        return not self.used and not self.is_expired()