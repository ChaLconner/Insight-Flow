"""
Tests for email service.
Covers EmailService with mocked Resend API and async operations.
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest


class TestEmailServiceConfiguration:
    """Tests for email service configuration handling."""

    @pytest.mark.asyncio
    async def test_send_email_missing_config_development(self):
        """Test that email is mocked in development when config missing."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "",
                "ENVIRONMENT": "development",
            },
            clear=False,
        ):
            result = await EmailService.send_email(
                "test@example.com", "Test Subject", "<p>Test content</p>"
            )
            # Should return True in development (mocked)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_missing_config_production(self):
        """Test that email fails in production when config missing."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "",
                "ENVIRONMENT": "production",
            },
            clear=False,
        ):
            result = await EmailService.send_email(
                "test@example.com", "Test Subject", "<p>Test content</p>"
            )
            # Should return False in production without config
            assert result is False


class TestEmailServiceSending:
    """Tests for email sending functionality."""

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test successful email sending via Resend API."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "re_test_api_key",
                "SENDER_EMAIL": "noreply@test.com",
            },
        ), patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = '{"id": "email_123"}'

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await EmailService.send_email(
                "recipient@example.com", "Test Subject", "<p>Test content</p>"
            )

            assert result is True
            mock_instance.post.assert_called_once()
            call_kwargs = mock_instance.post.call_args
            assert call_kwargs.kwargs["json"]["to"] == ["recipient@example.com"]
            assert call_kwargs.kwargs["json"]["subject"] == "Test Subject"

    @pytest.mark.asyncio
    async def test_send_email_api_error(self):
        """Test email sending with API error."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "re_test_api_key",
            },
        ), patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_response.text = '{"error": "Invalid API key"}'

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await EmailService.send_email(
                "recipient@example.com", "Test Subject", "<p>Test content</p>"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_default_sender(self):
        """Test email uses default sender when SENDER_EMAIL not explicitly set."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "re_test_api_key",
                "SENDER_EMAIL": "",  # Empty, should use default
            },
        ):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200

                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(return_value=mock_response)
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=None)
                mock_client.return_value = mock_instance

                result = await EmailService.send_email(
                    "recipient@example.com", "Test Subject", "<p>Test content</p>"
                )

                assert result is True


class TestEmailTemplates:
    """Tests for email template generation."""

    def test_base_template_structure(self):
        """Test that base template contains required elements."""
        from services.email_service import EmailService

        template = EmailService._get_base_template(
            subject="Welcome",
            content="<p>Welcome message</p>",
            action_url="https://example.com/verify",
            action_text="Verify Email",
        )

        # Check for key elements
        assert "<!DOCTYPE html>" in template
        assert "Insight Flow" in template
        assert "Welcome" in template
        assert "Welcome message" in template
        assert "https://example.com/verify" in template
        assert "Verify Email" in template

    def test_base_template_styling(self):
        """Test that base template includes CSS styles."""
        from services.email_service import EmailService

        template = EmailService._get_base_template(
            subject="Test",
            content="<p>Content</p>",
            action_url="https://example.com",
            action_text="Click",
        )

        # Check for styling elements
        assert "<style>" in template
        assert "font-family" in template
        assert "button" in template.lower()


class TestVerificationEmail:
    """Tests for verification email functionality."""

    @pytest.mark.asyncio
    async def test_send_verification_email_format(self):
        """Test verification email contains correct content."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "FRONTEND_URL": "http://localhost:3000",
                "ENVIRONMENT": "development",
            },
        ), patch.object(
            EmailService, "send_email", new=AsyncMock(return_value=True)
        ) as mock_send:
            result = await EmailService.send_verification_email(
                "user@example.com", "verification-token-123"
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args

            # Check email recipient
            assert call_args[0][0] == "user@example.com"
            # Check subject contains verification
            assert "Verify" in call_args[0][1]
            # Check HTML contains verification link
            html_content = call_args[0][2]
            assert "verification-token-123" in html_content
            assert "http://localhost:3000/auth/verify-email" in html_content

    @pytest.mark.asyncio
    async def test_verification_email_custom_frontend_url(self):
        """Test verification email uses custom frontend URL."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "FRONTEND_URL": "https://myapp.com",
                "ENVIRONMENT": "development",
            },
        ), patch.object(
            EmailService, "send_email", new=AsyncMock(return_value=True)
        ) as mock_send:
            await EmailService.send_verification_email("user@example.com", "token")

            html_content = mock_send.call_args[0][2]
            assert "https://myapp.com" in html_content


class TestPasswordResetEmail:
    """Tests for password reset email functionality."""

    @pytest.mark.asyncio
    async def test_send_password_reset_email_format(self):
        """Test password reset email contains correct content."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "FRONTEND_URL": "http://localhost:3000",
                "ENVIRONMENT": "development",
            },
        ), patch.object(
            EmailService, "send_email", new=AsyncMock(return_value=True)
        ) as mock_send:
            result = await EmailService.send_password_reset_email(
                "user@example.com", "reset-token-456"
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args

            # Check email recipient
            assert call_args[0][0] == "user@example.com"
            # Check subject contains reset
            assert "Reset" in call_args[0][1] or "reset" in call_args[0][1]
            # Check HTML contains reset link
            html_content = call_args[0][2]
            assert "reset-token-456" in html_content
            assert "reset-password" in html_content

    @pytest.mark.asyncio
    async def test_password_reset_email_content(self):
        """Test password reset email has appropriate messaging."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "FRONTEND_URL": "http://localhost:3000",
                "ENVIRONMENT": "development",
            },
        ), patch.object(
            EmailService, "send_email", new=AsyncMock(return_value=True)
        ) as mock_send:
            await EmailService.send_password_reset_email("user@example.com", "token")

            html_content = mock_send.call_args[0][2]
            # Should mention it was requested
            assert "request" in html_content.lower()
            # Should mention ignoring if not requested
            assert "ignore" in html_content.lower()


class TestEmailServiceErrorHandling:
    """Tests for error handling in email service."""

    @pytest.mark.asyncio
    async def test_send_email_catches_exceptions(self):
        """Test that send_email catches and handles exceptions gracefully."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "re_test_api_key",
            },
        ), patch("httpx.AsyncClient") as mock_client:
            # Simulate connection error
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=Exception("Connection error"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await EmailService.send_email("test@example.com", "Test", "<p>Test</p>")

            # Should return False, not raise exception
            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_timeout_handling(self):
        """Test email sending handles timeout gracefully."""
        import httpx

        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "re_test_api_key",
            },
        ), patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await EmailService.send_email("test@example.com", "Test", "<p>Test</p>")

            assert result is False


class TestEmailServiceAsync:
    """Tests for async behavior of email service."""

    @pytest.mark.asyncio
    async def test_multiple_emails_concurrent(self):
        """Test sending multiple emails concurrently."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "development",
                "RESEND_API_KEY": "",  # Will use mock mode
            },
        ):
            # Send multiple emails concurrently
            results = await asyncio.gather(
                EmailService.send_email("user1@test.com", "Test 1", "<p>1</p>"),
                EmailService.send_email("user2@test.com", "Test 2", "<p>2</p>"),
                EmailService.send_email("user3@test.com", "Test 3", "<p>3</p>"),
            )

            # All should succeed in dev mode
            assert all(results)


class TestAccountLockoutEmail:
    """Tests for account lockout notification email."""

    @pytest.mark.asyncio
    async def test_send_lockout_notification(self):
        """Test account lockout notification email is sent correctly."""
        from datetime import datetime

        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "FRONTEND_URL": "http://localhost:3000",
                "ENVIRONMENT": "development",
            },
        ), patch.object(
            EmailService, "send_email", new=AsyncMock(return_value=True)
        ) as mock_send:
            result = await EmailService.send_account_lockout_notification(
                "user@example.com",
                datetime(2026, 1, 5, 18, 0, 0),
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0 Test Browser",
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args

            # Check email recipient
            assert call_args[0][0] == "user@example.com"
            # Check subject contains security alert
            assert "Security" in call_args[0][1] or "Locked" in call_args[0][1]
            # Check HTML contains security details
            html_content = call_args[0][2]
            assert "192.168.1.1" in html_content
            assert "Mozilla/5.0 Test Browser" in html_content

    @pytest.mark.asyncio
    async def test_lockout_notification_xss_prevention(self):
        """Test that lockout notification sanitizes user input."""
        from services.email_service import EmailService

        with patch.dict(
            os.environ,
            {
                "FRONTEND_URL": "http://localhost:3000",
                "ENVIRONMENT": "development",
            },
        ), patch.object(
            EmailService, "send_email", new=AsyncMock(return_value=True)
        ) as mock_send:
            # Attempt XSS in user agent
            await EmailService.send_account_lockout_notification(
                "user@example.com",
                "2026-01-05 18:00:00",
                ip_address="<script>alert('xss')</script>",
                user_agent="<img onerror='alert(1)' src='x'>",
            )

            html_content = mock_send.call_args[0][2]
            # Should be escaped
            assert "<script>" not in html_content
            assert "<img" not in html_content
            assert "&lt;script&gt;" in html_content
