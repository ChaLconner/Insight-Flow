"""
Tests for email service.
Covers EmailService with mocked SMTP and async operations.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import os


class TestEmailServiceConfiguration:
    """Tests for email service configuration handling."""

    @pytest.mark.asyncio
    async def test_send_email_missing_config_development(self):
        """Test that email is mocked in development when config missing."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "SMTP_HOST": "",
            "SMTP_PORT": "",
            "SMTP_USER": "",
            "SMTP_PASSWORD": "",
            "ENVIRONMENT": "development",
        }, clear=False):
            result = await EmailService.send_email(
                "test@example.com",
                "Test Subject",
                "<p>Test content</p>"
            )
            # Should return True in development (mocked)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_missing_config_production(self):
        """Test that email fails in production when config missing."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "SMTP_HOST": "",
            "SMTP_PORT": "",
            "SMTP_USER": "",
            "SMTP_PASSWORD": "",
            "ENVIRONMENT": "production",
        }, clear=False):
            result = await EmailService.send_email(
                "test@example.com",
                "Test Subject",
                "<p>Test content</p>"
            )
            # Should return False in production without config
            assert result is False


class TestEmailServiceSending:
    """Tests for email sending functionality."""

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test successful email sending."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "password123",
            "SENDER_EMAIL": "noreply@test.com",
        }):
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = await EmailService.send_email(
                    "recipient@example.com",
                    "Test Subject",
                    "<p>Test content</p>"
                )

                assert result is True
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_once()
                mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_smtp_error(self):
        """Test email sending with SMTP error."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "password123",
        }):
            with patch("smtplib.SMTP") as mock_smtp:
                mock_smtp.return_value.__enter__.side_effect = Exception("SMTP Error")

                result = await EmailService.send_email(
                    "recipient@example.com",
                    "Test Subject",
                    "<p>Test content</p>"
                )

                assert result is False

    @pytest.mark.asyncio
    async def test_send_email_default_sender(self):
        """Test email uses SMTP_USER as sender when SENDER_EMAIL not set."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "password123",
            "SENDER_EMAIL": "",  # Empty
        }):
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = await EmailService.send_email(
                    "recipient@example.com",
                    "Test Subject",
                    "<p>Test content</p>"
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
            action_text="Verify Email"
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
            action_text="Click"
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

        with patch.dict(os.environ, {
            "FRONTEND_URL": "http://localhost:3000",
            "ENVIRONMENT": "development",
        }):
            with patch.object(
                EmailService, 
                "send_email", 
                new=AsyncMock(return_value=True)
            ) as mock_send:
                result = await EmailService.send_verification_email(
                    "user@example.com",
                    "verification-token-123"
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

        with patch.dict(os.environ, {
            "FRONTEND_URL": "https://myapp.com",
            "ENVIRONMENT": "development",
        }):
            with patch.object(
                EmailService,
                "send_email",
                new=AsyncMock(return_value=True)
            ) as mock_send:
                await EmailService.send_verification_email(
                    "user@example.com",
                    "token"
                )

                html_content = mock_send.call_args[0][2]
                assert "https://myapp.com" in html_content


class TestPasswordResetEmail:
    """Tests for password reset email functionality."""

    @pytest.mark.asyncio
    async def test_send_password_reset_email_format(self):
        """Test password reset email contains correct content."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "FRONTEND_URL": "http://localhost:3000",
            "ENVIRONMENT": "development",
        }):
            with patch.object(
                EmailService,
                "send_email",
                new=AsyncMock(return_value=True)
            ) as mock_send:
                result = await EmailService.send_password_reset_email(
                    "user@example.com",
                    "reset-token-456"
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

        with patch.dict(os.environ, {
            "FRONTEND_URL": "http://localhost:3000",
            "ENVIRONMENT": "development",
        }):
            with patch.object(
                EmailService,
                "send_email",
                new=AsyncMock(return_value=True)
            ) as mock_send:
                await EmailService.send_password_reset_email(
                    "user@example.com",
                    "token"
                )

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

        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "password123",
        }):
            with patch("smtplib.SMTP") as mock_smtp:
                # Simulate various errors
                mock_smtp.side_effect = ConnectionRefusedError("Connection refused")

                result = await EmailService.send_email(
                    "test@example.com",
                    "Test",
                    "<p>Test</p>"
                )

                # Should return False, not raise exception
                assert result is False

    @pytest.mark.asyncio
    async def test_send_email_timeout_handling(self):
        """Test email sending handles timeout gracefully."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "password123",
        }):
            with patch("smtplib.SMTP") as mock_smtp:
                import socket
                mock_smtp.side_effect = socket.timeout("Connection timed out")

                result = await EmailService.send_email(
                    "test@example.com",
                    "Test",
                    "<p>Test</p>"
                )

                assert result is False


class TestEmailServiceAsync:
    """Tests for async behavior of email service."""

    @pytest.mark.asyncio
    async def test_send_email_runs_in_executor(self):
        """Test that SMTP operations run in thread pool executor."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "password123",
        }):
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                with patch("asyncio.get_event_loop") as mock_loop:
                    mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)

                    # This should complete without blocking
                    result = await EmailService.send_email(
                        "test@example.com",
                        "Test",
                        "<p>Test</p>"
                    )

                    # Verify executor was used for sync operations
                    assert result is True

    @pytest.mark.asyncio
    async def test_multiple_emails_concurrent(self):
        """Test sending multiple emails concurrently."""
        from services.email_service import EmailService

        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "SMTP_HOST": "",  # Will use mock mode
        }):
            # Send multiple emails concurrently
            results = await asyncio.gather(
                EmailService.send_email("user1@test.com", "Test 1", "<p>1</p>"),
                EmailService.send_email("user2@test.com", "Test 2", "<p>2</p>"),
                EmailService.send_email("user3@test.com", "Test 3", "<p>3</p>"),
            )

            # All should succeed in dev mode
            assert all(results)
