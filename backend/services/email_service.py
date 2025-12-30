"""
Async Email service for sending system emails.
"""

import asyncio
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils.logger import mask_email, setup_logger

logger = setup_logger("email_service")


class EmailService:
    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email asynchronously (using thread pool).
        """
        try:
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = os.getenv("SMTP_PORT")
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            sender_email = os.getenv("SENDER_EMAIL", smtp_user)

            if not (smtp_host and smtp_port and smtp_user and smtp_password):
                # Mock email in development
                if os.getenv("ENVIRONMENT", "development") == "development":
                    logger.info(f"MOCK EMAIL SENT to {mask_email(to_email)} Subject: {subject}")
                    logger.debug(f"Content: {html_content[:100]}...")
                    return True
                logger.warning(
                    f"Email configuration missing. Failed to send email to {mask_email(to_email)}"
                )
                return False

            if not sender_email:
                sender_email = "noreply@example.com"

            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_content, "html"))

            def send_email_sync():
                with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_email_sync)
            logger.info(f"Email sent successfully to {mask_email(to_email)}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {mask_email(to_email)}: {e}")
            return False

    @staticmethod
    def _get_base_template(subject: str, content: str, action_url: str, action_text: str) -> str:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f9fafb; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-top: 40px; margin-bottom: 40px; }}
                .header {{ background: #4f46e5; padding: 24px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; font-weight: 600; letter-spacing: -0.5px; }}
                .content {{ padding: 32px; }}
                .button {{ display: inline-block; background-color: #4f46e5; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 24px; margin-bottom: 24px; }}
                .footer {{ background: #f3f4f6; padding: 24px; text-align: center; font-size: 14px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Insight Flow</h1>
                </div>
                <div class="content">
                    <h2 style="margin-top: 0; color: #111827;">{subject}</h2>
                    {content}
                    <div style="text-align: center;">
                        <a href="{action_url}" class="button">{action_text}</a>
                    </div>
                    <p style="font-size: 14px; color: #6b7280; margin-top: 24px;">Or copy this link to your browser:<br> <a href="{action_url}" style="color: #4f46e5;">{action_url}</a></p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 Insight Flow. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    async def send_verification_email(email: str, token: str) -> bool:
        """Send verification email."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        verification_link = f"{frontend_url}/auth/verify-email?token={token}"

        subject = "Verify your email address"
        content = """
        <p>Welcome to Insight Flow! We're excited to have you on board.</p>
        <p>Please verify your email address to get access to all features and start managing your projects properly.</p>
        """

        html_email = EmailService._get_base_template(
            subject, content, verification_link, "Verify Email"
        )
        return await EmailService.send_email(email, f"Insight Flow - {subject}", html_email)

    @staticmethod
    async def send_password_reset_email(email: str, token: str) -> bool:
        """Send password reset email."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend_url}/auth/reset-password?token={token}"

        subject = "Reset your password"
        content = """
        <p>We received a request to reset your password.</p>
        <p>If you didn't ask for this, you can ignore this email.</p>
        """
        html_email = EmailService._get_base_template(subject, content, reset_link, "Reset Password")
        return await EmailService.send_email(email, f"Insight Flow - {subject}", html_email)
