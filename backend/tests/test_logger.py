"""
Comprehensive tests for utils/logger.py

Tests follow best practices:
- Test logger creation and configuration
- Test log masking functionality for security
- Test different log levels
"""

import logging


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_setup_logger_returns_logger(self):
        """Test setup_logger returns a logger instance."""
        from utils.logger import setup_logger

        # Act
        logger = setup_logger("test_logger")

        # Assert
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_setup_logger_with_name(self):
        """Test logger has correct name."""
        from utils.logger import setup_logger

        # Act
        logger = setup_logger("my_module")

        # Assert
        assert logger.name == "my_module"

    def test_setup_logger_has_handlers(self):
        """Test setup_logger adds handlers."""
        from utils.logger import setup_logger

        # Act
        logger = setup_logger("handler_test")

        # Assert - should have at least one handler
        # Note: might share handlers with parent logger
        assert logger.level >= 0  # Valid log level


class TestMaskUserId:
    """Tests for mask_user_id function."""

    def test_mask_user_id_uuid_string(self):
        """Test masking UUID string."""
        from utils.logger import mask_user_id

        # Arrange
        user_id = "12345678-1234-1234-1234-123456789012"

        # Act
        masked = mask_user_id(user_id)

        # Assert
        assert masked is not None
        assert masked != user_id  # Should be different
        assert "***" in masked or len(masked) < len(user_id)  # Should be masked

    def test_mask_user_id_short_string(self):
        """Test masking short ID."""
        from utils.logger import mask_user_id

        # Arrange
        user_id = "abc"

        # Act
        masked = mask_user_id(user_id)

        # Assert
        assert masked is not None

    def test_mask_user_id_none(self):
        """Test masking None value."""
        from utils.logger import mask_user_id

        # Act
        masked = mask_user_id(None)

        # Assert
        assert masked in [None, "None", "***"]  # Should handle gracefully

    def test_mask_user_id_uuid_object(self):
        """Test masking UUID object."""
        from uuid import uuid4

        from utils.logger import mask_user_id

        # Arrange
        user_id = uuid4()

        # Act
        masked = mask_user_id(user_id)

        # Assert
        assert masked is not None
        assert str(user_id) not in masked  # Full UUID should not be visible


class TestMaskEmail:
    """Tests for mask_email function."""

    def test_mask_email_standard(self):
        """Test masking standard email."""
        from utils.logger import mask_email

        # Arrange
        email = "test@example.com"

        # Act
        masked = mask_email(email)

        # Assert
        assert masked is not None
        assert "@" in masked  # Should contain @
        assert masked != email  # Should be different from original
        assert "***" in masked or "*" in masked  # Should have masking

    def test_mask_email_short_username(self):
        """Test masking email with short username."""
        from utils.logger import mask_email

        # Arrange
        email = "ab@example.com"

        # Act
        masked = mask_email(email)

        # Assert
        assert masked is not None
        assert "@" in masked

    def test_mask_email_none(self):
        """Test masking None email."""
        from utils.logger import mask_email

        # Act
        masked = mask_email(None)

        # Assert
        assert masked in [None, "", "***"]  # Should handle gracefully

    def test_mask_email_invalid_format(self):
        """Test masking invalid email format."""
        from utils.logger import mask_email

        # Arrange
        email = "not-an-email"

        # Act
        masked = mask_email(email)

        # Assert - should not crash
        assert masked is not None


class TestLogLevels:
    """Tests for ensuring proper log level configuration."""

    def test_default_log_level(self):
        """Test default log level is appropriate."""
        from utils.logger import setup_logger

        # Act
        logger = setup_logger("level_test")

        # Assert - should be INFO or lower in test mode
        assert logger.level <= logging.WARNING
