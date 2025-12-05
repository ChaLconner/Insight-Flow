"""
Password reset service for handling password reset operations.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from models.user import User
from models.password_reset import PasswordReset
from services.user_service import UserService
from utils.logger import setup_logger
import os

logger = setup_logger("password_reset_service")

class PasswordResetService:
    """Service for handling password reset operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
    
    def create_password_reset_token(self, email: str) -> Optional[PasswordReset]:
        """
        Create a password reset token for the given email.
        
        Args:
            email: User's email address
            
        Returns:
            PasswordReset object if successful, None if user not found
        """
        # Check if user exists
        user = self.user_service.get_user_by_email(email)
        if not user:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return None
        
        # Invalidate any existing tokens for this email
        self.db.query(PasswordReset).filter(
            PasswordReset.email == email,
            PasswordReset.used == False
        ).update({"used": True})
        
        # Create new reset token
        reset_token, raw_token = PasswordReset.create_reset_token(email)
        self.db.add(reset_token)
        self.db.commit()
        self.db.refresh(reset_token)
        
        logger.info(f"Password reset token created for email: {email}")
        # Return object but attach raw_token for email sending
        reset_token.raw_token = raw_token
        return reset_token
    
    def validate_reset_token(self, token: str) -> Optional[PasswordReset]:
        """
        Validate a password reset token.
        
        Args:
            token: Password reset token (raw)
            
        Returns:
            PasswordReset object if valid, None otherwise
        """
        hashed_token = PasswordReset.hash_token(token)
        
        reset_token = self.db.query(PasswordReset).filter(
            PasswordReset.token == hashed_token,
            PasswordReset.used == False
        ).first()
        
        if not reset_token:
            logger.warning(f"Invalid or used reset token: {token}")
            return None
        
        if reset_token.is_expired():
            logger.warning(f"Expired reset token: {token}")
            return None
        
        return reset_token
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset user's password using a valid token.
        
        Args:
            token: Password reset token
            new_password: New password to set
            
        Returns:
            True if successful, False otherwise
        """
        # Validate token
        reset_token = self.validate_reset_token(token)
        if not reset_token:
            logger.warning(f"Password reset attempted with invalid token: {token}")
            return False
        
        # Get user
        user = self.user_service.get_user_by_email(reset_token.email)
        if not user:
            logger.error(f"User not found for email: {reset_token.email}")
            return False
        
        try:
            # Update user password
            user.hashed_password = self.user_service.hash_password(new_password)
            
            # Mark token as used
            reset_token.used = True
            
            self.db.commit()
            
            logger.info(f"Password reset successful for email: {reset_token.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting password for email {reset_token.email}: {e}")
            self.db.rollback()
            return False
    
    def send_reset_email(self, email: str, token: str) -> bool:
        """
        Send password reset email to user.
        
        Args:
            email: User's email address
            token: Password reset token
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # In development, just log the reset link
            if os.getenv("ENVIRONMENT", "development") == "development":
                reset_link = f"http://localhost:3000/auth/reset-password?token={token}"
                logger.info(f"MOCK EMAIL: Password reset link for {email}: {reset_link}")
                return True
            
            # In production, implement actual email sending
            # TODO: Implement real email service
            logger.warning(f"Email service not configured. Password reset token for {email}: {token}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending reset email to {email}: {e}")
            return False