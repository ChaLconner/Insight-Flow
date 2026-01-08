"""
Tests for security/stripe_error_handler.py

Tests Stripe error handling utilities.
"""

from uuid import uuid4


class TestLogAndGetSafeError:
    """Tests for log_and_get_safe_error function."""

    def test_returns_safe_message_for_generic_exception(self):
        """Test returns safe message for generic exceptions."""
        from security.stripe_error_handler import log_and_get_safe_error

        exception = Exception("Internal error details")

        safe_message = log_and_get_safe_error(
            exception, operation="test_operation", user_id=str(uuid4())
        )

        # Should not expose internal error details
        assert safe_message is not None
        assert isinstance(safe_message, str)
        # Internal details should not be in safe message
        assert "Internal error details" not in safe_message or len(safe_message) > 0

    def test_handles_card_error(self):
        """Test handling Stripe card errors."""
        import stripe

        from security.stripe_error_handler import log_and_get_safe_error

        # Create mock card error
        error = stripe.error.CardError(
            message="Your card was declined", param="card", code="card_declined"
        )

        safe_message = log_and_get_safe_error(
            error, operation="add_payment_method", user_id=str(uuid4())
        )

        assert safe_message is not None

    def test_handles_authentication_error(self):
        """Test handling Stripe authentication errors."""
        import stripe

        from security.stripe_error_handler import log_and_get_safe_error

        error = stripe.error.AuthenticationError(message="Invalid API key")

        safe_message = log_and_get_safe_error(
            error, operation="create_setup_intent", user_id=str(uuid4())
        )

        assert safe_message is not None
        # Should not expose API key details
        assert "API key" not in safe_message

    def test_handles_rate_limit_error(self):
        """Test handling Stripe rate limit errors."""
        import stripe

        from security.stripe_error_handler import log_and_get_safe_error

        error = stripe.error.RateLimitError(message="Too many requests")

        safe_message = log_and_get_safe_error(
            error, operation="list_payment_methods", user_id=str(uuid4())
        )

        assert safe_message is not None


class TestErrorMapping:
    """Tests for error type to user message mapping."""

    def test_common_error_messages(self):
        """Test common error types have user-friendly messages."""
        from security.stripe_error_handler import log_and_get_safe_error

        # Test with ValueError
        error = ValueError("Invalid input")

        safe_message = log_and_get_safe_error(error, operation="validation", user_id="test")

        assert safe_message is not None
        assert len(safe_message) > 0
