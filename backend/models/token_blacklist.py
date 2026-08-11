"""
Token blacklist model for managing revoked tokens.
"""

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from utils.logger import setup_logger

from .base import BaseModel

logger = setup_logger("token_blacklist")

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session


class TokenBlacklist(BaseModel):
    """
    Model for storing blacklisted tokens (revoked tokens).
    """

    __tablename__ = "token_blacklist"

    token_jti: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_token_blacklist_expires_at", "expires_at"),)

    def __repr__(self):
        return f"<TokenBlacklist(jti={self.token_jti}, expires_at={self.expires_at})>"

    @staticmethod
    async def _invalidate_cache(token_jti: str) -> None:
        """Remove any cached blacklist decision after a revocation write."""
        try:
            from services.cache_service import cache_service

            await cache_service.delete(f"blacklist:jti:{token_jti}")
        except Exception as exc:
            # Verification never trusts cached negative decisions, so a cache
            # outage cannot turn a successful revocation into an acceptance.
            logger.warning(f"Failed to invalidate token blacklist cache: {exc}")

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

        # Check if token exists in blacklist
        blacklisted_token = db_session.query(cls).filter(cls.token_jti == token_jti).first()

        return blacklisted_token is not None

    @classmethod
    def cleanup_expired_tokens(cls, db_session: "Session"):
        """
        Remove expired tokens from blacklist to keep the table clean.

        Args:
            db_session: Database session
        """
        current_time = datetime.now(UTC)
        db_session.query(cls).filter(cls.expires_at < current_time).delete()
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
        blacklisted_token = cls(token_jti=token_jti, expires_at=expires_at)
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

    # ==========================================
    # ASYNC METHODS
    # ==========================================

    @classmethod
    async def async_is_token_blacklisted(cls, db_session: "AsyncSession", token_jti: str) -> bool:
        """
        Check if a token is blacklisted (Async).
        """

        result = await db_session.execute(select(cls).filter(cls.token_jti == token_jti))
        blacklisted_token = result.scalars().first()

        return blacklisted_token is not None

    @classmethod
    async def async_get_blacklisted_token(
        cls, db_session: "AsyncSession", token_jti: str
    ) -> "TokenBlacklist | None":
        """
        Get blacklisted token details (Async).
        """
        result = await db_session.execute(select(cls).filter(cls.token_jti == token_jti))
        return result.scalars().first()

    @classmethod
    async def async_cleanup_expired_tokens(cls, db_session: "AsyncSession"):
        """
        Remove expired tokens from blacklist (Async).
        """
        current_time = datetime.now(UTC)
        await db_session.execute(delete(cls).where(cls.expires_at < current_time))
        await db_session.commit()

    @classmethod
    async def async_blacklist_token(
        cls, db_session: "AsyncSession", token_jti: str, expires_at: datetime
    ) -> bool:
        """Atomically claim a JTI for revocation.

        Returns ``True`` only for the request that inserted the JTI.  A
        duplicate is a replay (including a concurrent insert), so callers that
        rotate tokens can reject it instead of issuing another token pair.
        """
        # Clean up expired tokens probabilistically (10% chance) to reduce DB load
        if secrets.randbelow(10) == 0:
            await cls.async_cleanup_expired_tokens(db_session)

        # Check if already blacklisted
        result = await db_session.execute(select(cls).filter(cls.token_jti == token_jti))
        existing_token = result.scalars().first()

        if existing_token:
            await cls._invalidate_cache(token_jti)
            return False

        blacklisted_token = cls(token_jti=token_jti, expires_at=expires_at)
        db_session.add(blacklisted_token)
        try:
            await db_session.commit()
            await cls._invalidate_cache(token_jti)
            return True
        except IntegrityError:
            await db_session.rollback()
            await cls._invalidate_cache(token_jti)
            return False
