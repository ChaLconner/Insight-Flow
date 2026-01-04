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
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #374151; margin: 0; padding: 0; background-color: #f3f4f6; }}
                .container {{ max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); }}
                .header {{ background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%); padding: 32px 24px; text-align: center; }}
                .header h1 {{ color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.025em; text-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .content {{ padding: 40px 32px; background-color: #ffffff; }}
                .button-container {{ text-align: center; margin: 32px 0; }}
                .button {{ display: inline-block; background-color: #4f46e5; color: #ffffff !important; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2); transition: background-color 0.2s; }}
                .button:hover {{ background-color: #4338ca; }}
                .footer {{ background: #f9fafb; padding: 24px; text-align: center; font-size: 13px; color: #9ca3af; border-top: 1px solid #e5e7eb; }}
                .link-text {{ color: #4f46e5; word-break: break-all; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Insight Flow</h1>
                </div>
                <div class="content">
                    <h2 style="margin-top: 0; color: #111827; font-size: 20px; font-weight: 600; margin-bottom: 24px;">{subject}</h2>
                    <div style="font-size: 16px; color: #4b5563;">
                        {content}
                    </div>
                    <div class="button-container">
                        <a href="{action_url}" class="button">{action_text}</a>
                    </div>
                    <p style="font-size: 14px; color: #6b7280; margin-top: 32px; border-top: 1px solid #e5e7eb; padding-top: 24px;">
                        Or open this link in your browser:<br>
                        <a href="{action_url}" class="link-text">{action_url}</a>
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 Insight Flow. All rights reserved.</p>
                    <p>Designed for efficiency developers.</p>
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

        subject = "Please Verify Your Email Address"
        content = """
        <p>Dear User,</p>
        <p>Thank you for joining <strong>Insight Flow</strong>. We are delighted to have you on board.</p>
        <p>To ensure the security of your account and access our full suite of project management tools, please verify your email address by clicking the button below.</p>
        <p>This helps us confirm that you are the owner of this email account.</p>
        """

        html_email = EmailService._get_base_template(
            subject, content, verification_link, "Verify Account"
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

    @staticmethod
    async def send_account_lockout_notification(
        email: str,
        locked_until,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Send account lockout notification email.
        
        A+ Security Enhancement: Notifies users when their account is locked
        due to multiple failed login attempts, providing details about the 
        suspicious activity.
        """
        from datetime import datetime
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        support_link = f"{frontend_url}/support"
        
        # Format lockout time
        if isinstance(locked_until, datetime):
            lockout_time = locked_until.strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            lockout_time = str(locked_until)
        
        # Sanitize user agent for display (prevent XSS in email)
        safe_user_agent = (user_agent or "Unknown")[:100].replace("<", "&lt;").replace(">", "&gt;")
        safe_ip = (ip_address or "Unknown").replace("<", "&lt;").replace(">", "&gt;")
        
        subject = "🔒 Security Alert: Account Temporarily Locked"
        content = f"""
        <p style="color: #dc2626; font-weight: 600;">⚠️ Your account has been temporarily locked due to multiple failed login attempts.</p>
        
        <p>This security measure helps protect your account from unauthorized access.</p>
        
        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 16px; margin: 16px 0;">
            <p style="margin: 0 0 8px 0;"><strong>Details of the login attempts:</strong></p>
            <p style="margin: 4px 0; font-size: 14px;">📍 IP Address: <code>{safe_ip}</code></p>
            <p style="margin: 4px 0; font-size: 14px;">🌐 Device: <code>{safe_user_agent}</code></p>
            <p style="margin: 4px 0; font-size: 14px;">⏰ Locked until: <code>{lockout_time}</code></p>
        </div>
        
        <p><strong>If this was you:</strong> Please wait until the lockout period expires, then try logging in again with the correct password.</p>
        
        <p><strong>If this wasn't you:</strong> Someone may be trying to access your account. We recommend:</p>
        <ul style="margin: 8px 0;">
            <li>Change your password immediately after the lockout expires</li>
            <li>Enable two-factor authentication if available</li>
            <li>Review your recent account activity</li>
        </ul>
        """
        
        html_email = EmailService._get_base_template(
            subject, content, support_link, "Contact Support"
        )
        return await EmailService.send_email(email, f"Insight Flow - {subject}", html_email)

