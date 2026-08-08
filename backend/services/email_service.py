"""
Async Email service for sending system emails using Resend.
"""

import os
from datetime import datetime

import httpx

from utils.logger import mask_email, setup_logger

logger = setup_logger("email_service")


class EmailService:
    """Email service using Resend API."""

    RESEND_API_URL = "https://api.resend.com/emails"
    _async_client: httpx.AsyncClient | None = None

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
        if cls._async_client is None or cls._async_client.is_closed:
            cls._async_client = httpx.AsyncClient(timeout=30.0)
        return cls._async_client

    @classmethod
    async def close(cls) -> None:
        """Close the shared HTTP client during worker/application shutdown."""
        if cls._async_client is not None and not cls._async_client.is_closed:
            await cls._async_client.aclose()
        cls._async_client = None

    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email asynchronously using Resend API.
        """
        try:
            api_key = os.getenv("RESEND_API_KEY")
            sender_email = os.getenv("SENDER_EMAIL", "Insight Flow <onboarding@resend.dev>")

            if not api_key:
                # Mock email in development
                if os.getenv("ENVIRONMENT", "development") == "development":
                    logger.info(f"MOCK EMAIL SENT to {mask_email(to_email)} Subject: {subject}")
                    logger.debug(f"Content: {html_content[:100]}...")
                    return True
                logger.warning(
                    f"RESEND_API_KEY not configured. Failed to send email to {mask_email(to_email)}"
                )
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "from": sender_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            client = EmailService._get_client()
            response = await client.post(
                EmailService.RESEND_API_URL, headers=headers, json=payload, timeout=30.0
            )

            if response.status_code == 200:
                logger.info(f"Email sent successfully to {mask_email(to_email)}")
                return True
            else:
                logger.error(
                    f"Failed to send email to {mask_email(to_email)}: "
                    f"Status {response.status_code}, Response: {response.text}"
                )
                return False

        except httpx.TimeoutException:
            logger.error(f"Timeout sending email to {mask_email(to_email)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email to {mask_email(to_email)}: {e}")
            return False

    @staticmethod
    def _get_base_template(subject: str, content: str, action_url: str, action_text: str) -> str:
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <!--[if mso]>
            <noscript>
            <xml>
              <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
              </o:OfficeDocumentSettings>
            </xml>
            </noscript>
            <![endif]-->
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                        'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #374151;
                    margin: 0;
                    padding: 0;
                    background-color: #f9fafb;
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                }}

                table {{
                    border-collapse: collapse;
                    width: 100%;
                }}

                .wrapper {{
                    width: 100%;
                    background-color: #f9fafb;
                    padding: 40px 20px;
                }}

                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    border: 1px solid #e5e7eb;
                }}

                .header {{
                    padding: 32px 40px;
                    background-color: #ffffff;
                    border-bottom: 1px solid #f3f4f6;
                    text-align: center;
                }}

                .logo-text {{
                    font-size: 24px;
                    font-weight: 800;
                    color: #4f46e5;
                    text-decoration: none;
                    letter-spacing: -0.5px;
                }}

                .content {{
                    padding: 40px 40px 32px;
                    background-color: #ffffff;
                }}

                h1 {{
                    margin-top: 0;
                    color: #111827;
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 16px;
                    text-align: center;
                }}

                .text-body {{
                    font-size: 16px;
                    color: #4b5563;
                    margin-bottom: 24px;
                    text-align: left;
                }}

                .text-body p {{
                    margin-bottom: 16px;
                }}

                .button-container {{
                    text-align: center;
                    margin: 32px 0;
                }}

                .button {{
                    display: inline-block;
                    background-color: #4f46e5;
                    color: #ffffff !important;
                    padding: 16px 36px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 16px;
                    box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2);
                    transition: all 0.2s ease;
                }}

                .button:hover {{
                    background-color: #4338ca;
                    box-shadow: 0 6px 8px -1px rgba(79, 70, 229, 0.3);
                    transform: translateY(-1px);
                }}

                .divider {{
                    height: 1px;
                    background-color: #e5e7eb;
                    margin: 32px 0;
                }}

                .footer {{
                    background-color: #f9fafb;
                    padding: 32px 40px;
                    text-align: center;
                    border-top: 1px solid #f3f4f6;
                }}

                .footer-text {{
                    font-size: 13px;
                    color: #6b7280;
                    margin-bottom: 12px;
                }}

                .link-text {{
                    color: #4f46e5;
                    word-break: break-all;
                    font-weight: 500;
                }}

                .help-text {{
                    font-size: 14px;
                    color: #9ca3af;
                    margin-top: 24px;
                }}

                @media only screen and (max-width: 600px) {{
                    .wrapper {{
                        padding: 20px 10px;
                    }}
                    .container {{
                        width: 100% !important;
                        border-radius: 12px;
                    }}
                    .header {{
                        padding: 24px 20px;
                    }}
                    .content {{
                        padding: 32px 24px;
                    }}
                    .button {{
                        display: block;
                        width: auto;
                        text-align: center;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="wrapper">
                <div class="container">
                    <div class="header">
                        <a href="https://insightflow.app" class="logo-text">Insight Flow</a>
                    </div>

                    <div class="content">
                        <!-- Hero Icon (Optional, can be added if we have a hosted image) -->

                        <h1>{subject}</h1>

                        <div class="text-body">
                            {content}
                        </div>

                        <div class="button-container">
                            <a href="{action_url}" class="button">{action_text}</a>
                        </div>

                        <div class="divider"></div>

                        <p style="font-size: 14px; color: #6b7280;">
                            Having trouble clicking the button? Copy and paste this link into your browser:
                            <br>
                            <a href="{action_url}" class="link-text">{action_url}</a>
                        </p>
                    </div>

                    <div class="footer">
                        <p class="footer-text">&copy; {datetime.now().year} Insight Flow. All rights reserved.</p>
                        <p class="footer-text">
                            You received this email because you signed up for Insight Flow.
                            <br>
                            If you didn't request this, you can safely ignore this email.
                        </p>
                    </div>
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
        <p>To ensure the security of your account and access our full suite of project management tools,
        please verify your email address by clicking the button below.</p>
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
        <p style="color: #dc2626; font-weight: 600;">
            ⚠️ Your account has been temporarily locked due to multiple failed login attempts.
        </p>

        <p>This security measure helps protect your account from unauthorized access.</p>

        <div style="background: #fef2f2; border: 1px solid #fecaca;
                    border-radius: 8px; padding: 16px; margin: 16px 0;">
            <p style="margin: 0 0 8px 0;"><strong>Details of the login attempts:</strong></p>
            <p style="margin: 4px 0; font-size: 14px;">
                📍 IP Address: <code>{safe_ip}</code>
            </p>
            <p style="margin: 4px 0; font-size: 14px;">
                🌐 Device: <code>{safe_user_agent}</code>
            </p>
            <p style="margin: 4px 0; font-size: 14px;">
                ⏰ Locked until: <code>{lockout_time}</code>
            </p>
        </div>

        <p><strong>If this was you:</strong> Please wait until the lockout period expires,
        then try logging in again with the correct password.</p>

        <p><strong>If this wasn't you:</strong> Someone may be trying to access your account.
        We recommend:</p>
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
