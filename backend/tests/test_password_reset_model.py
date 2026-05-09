"""
Tests for PasswordReset model.
Covers models/password_reset.py for increased coverage.
"""

import hashlib
from datetime import UTC, datetime, timedelta


class TestPasswordResetModel:
    """Tests for PasswordReset model static methods and instance methods."""

    def test_generate_token_returns_string(self):
        """Test that generate_token returns a string."""
        from models.password_reset import PasswordReset

        token = PasswordReset.generate_token()

        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_is_url_safe(self):
        """Test that generated token is URL safe."""
        from models.password_reset import PasswordReset

        token = PasswordReset.generate_token()

        # URL safe tokens should not contain +, /, =
        assert "+" not in token
        assert "/" not in token

    def test_generate_token_is_unique(self):
        """Test that each call generates a unique token."""
        from models.password_reset import PasswordReset

        tokens = [PasswordReset.generate_token() for _ in range(100)]

        # All tokens should be unique
        assert len(set(tokens)) == 100

    def test_hash_token_returns_sha256_hex(self):
        """Test that hash_token returns a SHA256 hex digest."""
        from models.password_reset import PasswordReset

        token = "test_token_123"
        hashed = PasswordReset.hash_token(token)

        # SHA256 hex digest should be 64 characters
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_token_is_deterministic(self):
        """Test that hashing same token produces same result."""
        from models.password_reset import PasswordReset

        token = "test_token_abc"
        hash1 = PasswordReset.hash_token(token)
        hash2 = PasswordReset.hash_token(token)

        assert hash1 == hash2

    def test_hash_token_matches_hashlib(self):
        """Test that hash_token produces correct SHA256 hash."""
        from models.password_reset import PasswordReset

        token = "my_secret_token"
        expected = hashlib.sha256(token.encode()).hexdigest()
        actual = PasswordReset.hash_token(token)

        assert actual == expected

    def test_create_reset_token_returns_tuple(self):
        """Test that create_reset_token returns tuple of (PasswordReset, raw_token)."""
        from models.password_reset import PasswordReset

        reset_token, raw_token = PasswordReset.create_reset_token("test@example.com")

        assert isinstance(reset_token, PasswordReset)
        assert isinstance(raw_token, str)

    def test_create_reset_token_sets_email(self):
        """Test that create_reset_token sets email correctly."""
        from models.password_reset import PasswordReset

        email = "user@test.com"
        reset_token, _ = PasswordReset.create_reset_token(email)

        assert reset_token.email == email

    def test_create_reset_token_hashes_token(self):
        """Test that create_reset_token stores hashed token."""
        from models.password_reset import PasswordReset

        reset_token, raw_token = PasswordReset.create_reset_token("test@example.com")

        # The stored token should be the hash of the raw token
        expected_hash = PasswordReset.hash_token(raw_token)
        assert reset_token.token == expected_hash

    def test_create_reset_token_sets_expiration(self):
        """Test that create_reset_token sets correct expiration."""
        from models.password_reset import PasswordReset

        reset_token, _ = PasswordReset.create_reset_token("test@example.com", expires_hours=2)

        # Expiration should be approximately 2 hours from now
        expected_min = datetime.now(UTC) + timedelta(hours=1, minutes=59)
        expected_max = datetime.now(UTC) + timedelta(hours=2, minutes=1)

        assert expected_min < reset_token.expires_at < expected_max

    def test_create_reset_token_default_expiration(self):
        """Test that create_reset_token uses 1 hour default expiration."""
        from models.password_reset import PasswordReset

        reset_token, _ = PasswordReset.create_reset_token("test@example.com")

        # Default is 1 hour
        expected_min = datetime.now(UTC) + timedelta(minutes=59)
        expected_max = datetime.now(UTC) + timedelta(hours=1, minutes=1)

        assert expected_min < reset_token.expires_at < expected_max

    def test_is_expired_returns_false_for_valid_token(self):
        """Test that is_expired returns False for non-expired token."""
        from models.password_reset import PasswordReset

        reset_token, _ = PasswordReset.create_reset_token("test@example.com", expires_hours=1)

        assert reset_token.is_expired() is False

    def test_is_expired_returns_true_for_expired_token(self):
        """Test that is_expired returns True for expired token."""
        from models.password_reset import PasswordReset

        reset_token = PasswordReset(
            email="test@example.com",
            token="hashed_token",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        assert reset_token.is_expired() is True

    def test_is_expired_handles_naive_database_datetime_as_utc(self):
        """Test that database-loaded naive datetimes are treated as UTC."""
        from models.password_reset import PasswordReset

        reset_token = PasswordReset(
            email="test@example.com",
            token="hashed_token",
            expires_at=datetime.now().replace(tzinfo=None) + timedelta(hours=1),
        )

        assert reset_token.is_expired() is False

    def test_is_valid_returns_true_for_fresh_unused_token(self):
        """Test that is_valid returns True for fresh, unused token."""
        from models.password_reset import PasswordReset

        reset_token, _ = PasswordReset.create_reset_token("test@example.com")

        assert reset_token.is_valid() is True

    def test_is_valid_returns_false_for_used_token(self):
        """Test that is_valid returns False for used token."""
        from models.password_reset import PasswordReset

        reset_token, _ = PasswordReset.create_reset_token("test@example.com")
        reset_token.used = True

        assert reset_token.is_valid() is False

    def test_is_valid_returns_false_for_expired_token(self):
        """Test that is_valid returns False for expired token."""
        from models.password_reset import PasswordReset

        reset_token = PasswordReset(
            email="test@example.com",
            token="hashed_token",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            used=False,
        )

        assert reset_token.is_valid() is False

    def test_is_valid_returns_false_for_used_and_expired_token(self):
        """Test that is_valid returns False for both used and expired token."""
        from models.password_reset import PasswordReset

        reset_token = PasswordReset(
            email="test@example.com",
            token="hashed_token",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            used=True,
        )

        assert reset_token.is_valid() is False

    def test_tablename_is_correct(self):
        """Test that the table name is password_resets."""
        from models.password_reset import PasswordReset

        assert PasswordReset.__tablename__ == "password_resets"

    def test_token_length_is_secure(self):
        """Test that generated tokens have sufficient length for security."""
        from models.password_reset import PasswordReset

        token = PasswordReset.generate_token()

        # secrets.token_urlsafe(32) produces ~43 character string
        # This provides at least 256 bits of entropy
        assert len(token) >= 40
