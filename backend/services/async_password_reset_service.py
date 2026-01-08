"""
Async Password reset service for handling password reset operations.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.password_reset import PasswordReset
from services.async_user_service import AsyncUserService
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
        self.db.add(reset_token)
        await self.db.commit()
        await self.db.refresh(reset_token)

        logger.info(f"Password reset token created for email: {mask_email(email)}")
        # Return object but attach raw_token for email sending
        reset_token.raw_token = raw_token
        # Validate type
        if not isinstance(reset_token, PasswordReset):
            raise ValueError("Invalid token type")
        return reset_token

    async def validate_reset_token(self, token: str) -> PasswordReset | None:
        """
        Validate a password reset token.
        """
        hashed_token = PasswordReset.hash_token(token)

        result = await self.db.execute(
            select(PasswordReset).filter(
                PasswordReset.token == hashed_token, PasswordReset.used.is_(False)
            )
        )
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
        reset_token = await self.validate_reset_token(token)
        if not reset_token:
            logger.warning(f"Password reset attempted with invalid token: {mask_token(token)}")
            return False

        # Get user
        user = await self.user_service.get_user_by_email(reset_token.email)
        if not user:
            logger.error(f"User not found for email: {mask_email(reset_token.email)}")
            return False

        try:
            # Update user password (userService.hash_password is sync or async? sync usually)
            # Checking UserService... it calls get_password_hash which is sync.
            # We can recreate hash_password here or use sync method.
            from utils.auth import get_password_hash

            user.hashed_password = get_password_hash(new_password)

            # Mark token as used
            reset_token.used = True

            await self.db.commit()

            logger.info(f"Password reset successful for email: {mask_email(reset_token.email)}")
            return True

        except Exception as e:
            logger.error(f"Error resetting password for email {mask_email(reset_token.email)}: {e}")
            await self.db.rollback()
            return False

    async def send_reset_email(self, email: str, token: str) -> bool:
        """
        Send password reset email to user in the background (non-blocking).

        This method returns immediately and the email is sent asynchronously.
        Any errors during email sending are logged but do not affect the caller.
        """
        from utils.background_tasks import fire_and_forget

        # Fire and forget - don't wait for email to be sent
        fire_and_forget(self._send_reset_email_internal(email, token))

        # Always return True since we've queued the email
        # Actual send errors will be logged in the background task
        logger.info(f"Password reset email queued for {mask_email(email)}")
        return True

    async def _send_reset_email_internal(self, email: str, token: str) -> None:
        """
        Internal method that actually sends the reset email.
        Called as a background task - errors are logged but not raised.
        """
        try:
            from services.email_service import EmailService

            result = await EmailService.send_password_reset_email(email, token)

            if result:
                logger.info(f"Password reset email sent successfully to {mask_email(email)}")
            else:
                logger.warning(f"Failed to send password reset email to {mask_email(email)}")

        except Exception as e:
            logger.error(f"Error sending reset email to {mask_email(email)}: {e}")
