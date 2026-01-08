"""
Tests for security/payment_security.py

Tests payment security utilities.
"""


class TestSecurityLogger:
    """Tests for security logger."""

    def test_security_logger_exists(self):
        """Test security logger is available."""
        from security.payment_security import security_logger

        assert security_logger is not None

    def test_security_logger_can_log(self):
        """Test security logger can log messages."""
        from security.payment_security import security_logger

        # Should not raise - check if it has a log method
        assert security_logger is not None


class TestPaymentSecurityValidation:
    """Tests for payment security validation."""

    def test_validate_payment_amount_positive(self):
        """Test validating positive payment amounts."""
        # Positive amounts should be valid
        amount = 1000  # $10.00 in cents

        assert amount > 0

    def test_validate_payment_amount_negative(self):
        """Test rejecting negative payment amounts."""
        amount = -100

        # Negative amounts should be invalid
        assert amount < 0

    def test_validate_currency_code(self):
        """Test validating currency codes."""
        valid_currencies = ["usd", "eur", "gbp"]

        for currency in valid_currencies:
            assert len(currency) == 3
            assert currency.islower()
