"""
Token blacklist model for managing revoked tokens.
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, DateTime, Integer
from .base import BaseModel
from utils.logger import setup_logger

logger = setup_logger("token_blacklist")

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class TokenBlacklist(BaseModel):
    """
    Model for storing blacklisted tokens (revoked tokens).
    """
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token_jti = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<TokenBlacklist(jti={self.token_jti}, expires_at={self.expires_at})>"

    @classmethod
    def is_token_blacklisted(cls, db_session: "Session", token_jti: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            db_session: Database session
            token_jti: JWT ID of the token to check
            
        Returns:
            bool: True if token is blacklisted, False otherwise
        """
        # Probabilistic cleanup (1% chance) to avoid overhead on every request
        import random
        if random.random() < 0.01:
            cls.cleanup_expired_tokens(db_session)
        
        # Check if token exists in blacklist
        blacklisted_token = db_session.query(cls).filter(
            cls.token_jti == token_jti
        ).first()
        
        return blacklisted_token is not None

    @classmethod
    def cleanup_expired_tokens(cls, db_session: "Session"):
        """
        Remove expired tokens from blacklist to keep the table clean.
        
        Args:
            db_session: Database session
        """
        current_time = datetime.now(timezone.utc)
        db_session.query(cls).filter(
            cls.expires_at < current_time
        ).delete()
        db_session.commit()

    @classmethod
    def blacklist_token(cls, db_session: "Session", token_jti: str, expires_at: datetime):
        """
        Add a token to the blacklist.
        
        Args:
            db_session: Database session
            token_jti: JWT ID of the token to blacklist
            expires_at: Expiration time of the token
        """
        # Clean up expired tokens first
        cls.cleanup_expired_tokens(db_session)
        
        # Check if token is already blacklisted
        existing_token = db_session.query(cls).filter(cls.token_jti == token_jti).first()
        if existing_token:
            return
        
        # Add token to blacklist
        blacklisted_token = cls(
            token_jti=token_jti,
            expires_at=expires_at
        )
        db_session.add(blacklisted_token)
        try:
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            # Check if it's a duplicate key error
            if "duplicate key" in str(e).lower():
                return
            else:
                raise e