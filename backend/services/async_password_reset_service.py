"""
Async Password reset service for handling password reset operations.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import os

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
            .where(PasswordReset.email == email, PasswordReset.used == False)
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
                PasswordReset.token == hashed_token, PasswordReset.used == False
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
        Send password reset email to user. (Same logic as Sync, but safe to run in async context as it is IO bound/blocking,
        but strictly, smtp should be run in a threadpool or background task if we want true async,
        however, for now we will keep it simple or wrap in run_in_executor if needed.
        Given it's critical path for user flow, blocking briefly is often accepted or offloaded to celery/background tasks.
        For now, we'll keep the logic identical.)
        """
        # Reuse the existing synchronous send logic or duplicate it.
        # Since it uses smtplib which is blocking, we should strictly run it in a threadpool.
        # But for migration simplicity, we will copy the logic.

        try:
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = os.getenv("SMTP_PORT")
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            sender_email = os.getenv("SENDER_EMAIL", smtp_user)

            reset_link = f"http://localhost:3000/auth/reset-password?token={token}"

            if smtp_host and smtp_port and smtp_user and smtp_password:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText

                if not sender_email:
                    sender_email = "noreply@example.com"

                msg = MIMEMultipart()
                msg["From"] = sender_email
                msg["To"] = email
                msg["Subject"] = "Insight-Flow Password Reset Request"

                body = f"""
                <p>Hello,</p>
                <p>You have requested to reset your password for Insight-Flow.</p>
                <p>Please click the link below to verify your email and reset your password:</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>If you did not request this, please ignore this email.</p>
                <p>This link will expire in 30 minutes.</p>
                <br>
                <p>Best regards,</p>
                <p>The Insight-Flow Team</p>
                """

                msg.attach(MIMEText(body, "html"))

                # Run blocking SMTP in thread
                import asyncio

                loop = asyncio.get_event_loop()

                def send_email_sync():
                    server = smtplib.SMTP(smtp_host, int(smtp_port))
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    text = msg.as_string()
                    server.sendmail(sender_email, email, text)
                    server.quit()

                await loop.run_in_executor(None, send_email_sync)

                logger.info(f"Password reset email sent successfully to {mask_email(email)}")
                return True

            # Default/Fallback
            if os.getenv("ENVIRONMENT", "development") == "development":
                logger.info(f"MOCK EMAIL: Password reset link generated for {mask_email(email)}")
                return True

            logger.warning(f"Email service not configured for: {mask_email(email)}")
            return True

        except Exception as e:
            logger.error(f"Error sending reset email to {mask_email(email)}: {e}")
            return False
