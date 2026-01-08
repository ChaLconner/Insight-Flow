from utils.error_messages import ErrorCodes, ErrorMessages, format_error


class TestErrorUtils:
    def test_format_error_success(self):
        """Test formatting error with arguments."""
        template = "File too large: {max_size}MB"
        result = format_error(template, max_size=50)
        assert result == "File too large: 50MB"

    def test_format_error_missing_args(self):
        """Test formatting error with missing args (should return template safely)."""
        template = "File too large: {max_size}MB"
        result = format_error(template)
        assert result == template

    def test_error_messages_constants(self):
        """Test that some error messages are defined."""
        assert ErrorMessages.AUTH_INVALID_CREDENTIALS is not None
        assert "password" in ErrorMessages.AUTH_INVALID_CREDENTIALS.lower()

    def test_error_codes_constants(self):
        """Test that some error codes are defined."""
        assert ErrorCodes.AUTH_INVALID_CREDENTIALS == "AUTH_001"
