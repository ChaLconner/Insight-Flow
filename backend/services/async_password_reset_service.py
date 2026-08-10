"""
Async Password reset service for handling password reset operations.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.password_reset import PasswordReset
from services.async_user_service import AsyncUserService
from services.cache_invalidation import invalidate_auth_user_cache
from services.job_payload_security import encrypt_job_secret
from services.job_queue import enqueue_job
from utils.logger import mask_email, mask_token, setup_logger

logger = setup_logger("async_password_reset_service")


class AsyncPasswordResetService:
    """Async Service for handling password reset operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = AsyncUserService(db)

    async def create_password_reset_token(self, email: str) -> PasswordReset | None:
        """
        Create a password reset token for the given email.
        """
        # Check if user exists
        user = await self.user_service.get_user_by_email(email)
        if not user:
            logger.warning(f"Password reset requested for non-existent email: {mask_email(email)}")
            return None

        # Invalidate any existing tokens for this email
        await self.db.execute(
            update(PasswordReset)
            .where(PasswordReset.email == email, PasswordReset.used.is_(False))
            .values(used=True)
        )

        # Create new reset token
        # Note: create_reset_token likely returns a non-persistent object, which is fine
        reset_token, raw_token = PasswordReset.create_reset_token(email)
        try:
            self.db.add(reset_token)
            await enqueue_job(
                self.db,
                "email.send",
                {
                    "method": "password_reset",
                    "email": email,
                    "token_encrypted": encrypt_job_secret(raw_token),
                },
                idempotency_key=f"password-reset:{email}:{PasswordReset.hash_token(raw_token)}",
            )
            await self.db.commit()
            await self.db.refresh(reset_token)
        except Exception:
            await self.db.rollback()
            raise

        logger.info(f"Password reset token created for email: {mask_email(email)}")
        # Return object but attach raw_token for email sending
        reset_token.raw_token = raw_token
        # Validate type
        if not isinstance(reset_token, PasswordReset):
            raise ValueError("Invalid token type")
        return reset_token

    async def validate_reset_token(
        self, token: str, *, for_update: bool = False
    ) -> PasswordReset | None:
        """
        Validate a password reset token.
        """
        hashed_token = PasswordReset.hash_token(token)

        statement = select(PasswordReset).filter(
            PasswordReset.token == hashed_token, PasswordReset.used.is_(False)
        )
        if for_update:
            statement = statement.with_for_update()

        result = await self.db.execute(statement)
        reset_token = result.scalars().first()

        if not reset_token:
            logger.warning(f"Invalid or used reset token: {mask_token(token)}")
            return None

        if reset_token.is_expired():
            logger.warning(f"Expired reset token: {mask_token(token)}")
            return None

        return reset_token

    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset user's password using a valid token.
        """
        # Validate token
        # Lock the one-time token for the whole transaction.  Two concurrent
        # requests cannot both observe ``used = false`` and change a password.
        reset_token = await self.validate_reset_token(token, for_update=True)
        if not reset_token:
            logger.warning(f"Password reset attempted with invalid token: {mask_token(token)}")
            return False

        # Get user
        user = await self.user_service.get_user_by_email(reset_token.email)
        if not user:
            logger.error(f"User not found for email: {mask_email(reset_token.email)}")
            return False

        try:
            user.hashed_password = await self.user_service.hash_password(new_password)
            current_session_version = getattr(user, "session_version", 0)
            user.session_version = (
                current_session_version + 1 if isinstance(current_session_version, int) else 1
            )

            # Mark token as used
            reset_token.used = True

            await self.db.commit()
            await invalidate_auth_user_cache(user.id)

            logger.info(f"Password reset successful for email: {mask_email(reset_token.email)}")
            return True

        except Exception as e:
            logger.error(f"Error resetting password for email {mask_email(reset_token.email)}: {e}")
            await self.db.rollback()
            return False

    async def send_reset_email(self, email: str, token: str) -> bool:
        """
        Queue a password reset email for legacy callers.

        The worker performs delivery asynchronously. The idempotency key makes
        this safe when a caller retries after token creation already queued it.
        """
        try:
            await enqueue_job(
                self.db,
                "email.send",
                {
                    "method": "password_reset",
                    "email": email,
                    "token_encrypted": encrypt_job_secret(token),
                },
                idempotency_key=f"password-reset:{email}:{PasswordReset.hash_token(token)}",
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        logger.info(f"Password reset email queued for {mask_email(email)}")
        return True
