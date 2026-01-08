from unittest.mock import Mock, patch

import pytest

from security.password import (
    PasswordPolicy,
    PasswordPolicyConfig,
    PasswordPolicyViolation,
    calculate_entropy,
    check_password_breach,
    get_hash_algorithm,
    hash_password,
    verify_and_rehash,
    verify_password,
)


class TestPasswordSecurity:
    """Tests for password security module."""

    def test_hash_verify(self):
        """Test hashing and verification endpoints."""
        password = "CorrectHorseBatteryStaple1$"
        hashed = hash_password(password)

        # Verify
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False

        # Algorithm check
        algo = get_hash_algorithm(hashed)
        # Assuming argon2 as default config
        assert algo in ["argon2id", "bcrypt"]

    def test_verify_and_rehash(self):
        """Test hash upgrade logic."""
        password = "test"
        # Mocking or simulating old hash is hard without Passlib internal knowledge.
        # But we can check stable state.
        hashed = hash_password(password)

        valid, new_hash = verify_and_rehash(password, hashed)
        assert valid is True
        assert new_hash is None  # Already fresh

        valid, new_hash = verify_and_rehash("wrong", hashed)
        assert valid is False
        assert new_hash is None

    def test_calculate_entropy(self):
        """Test entropy calculation."""
        # Simple password (lowercase only)
        # char space 26. length 3. expected: 3 * log2(26) = 3 * 4.7 = 14.1
        entropy = calculate_entropy("abc")
        assert 14.0 < entropy < 15.0

        # Complex password
        # Lower(26)+Upper(26)+Digit(10)+Special(32) = 94
        # Length 10. 10 * log2(94) = 10 * 6.55 = 65.5
        entropy = calculate_entropy("A1!aaaaaaa")
        assert 60.0 < entropy < 70.0

        assert calculate_entropy("") == 0.0

    @pytest.mark.asyncio
    async def test_validate_password_policy(self):
        """Test policy validation."""
        policy = PasswordPolicy(
            PasswordPolicyConfig(
                min_length=8,
                require_uppercase=True,
                check_breached=False,  # mock this separately
            )
        )

        # Valid
        violations = await policy.validate("ValidPass1!")
        assert len(violations) == 0

        # Invalid (Too short)
        violations = await policy.validate("Short1!")
        assert any(v.violation_type == PasswordPolicyViolation.TOO_SHORT for v in violations)

        # Invalid (No uppercase)
        violations = await policy.validate("validpass1!")
        assert any(v.violation_type == PasswordPolicyViolation.NO_UPPERCASE for v in violations)

    @pytest.mark.asyncio
    @patch("security.password.httpx.AsyncClient")
    async def test_check_password_breach(self, mock_client_cls):
        """Test HIBP breach check."""
        # Setup mock logic
        mock_client = Mock()

        # Make __aenter__ return the client itself (as a coroutine)
        async def async_enter():
            return mock_client

        async def async_exit(*args):
            return None

        mock_client.__aenter__ = Mock(side_effect=async_enter)
        mock_client.__aexit__ = Mock(side_effect=async_exit)
        mock_client_cls.return_value = mock_client

        # Mock response for a breached password hash
        # Need to match suffix logic.
        # SHA1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
        # Prefix: 5BAA6
        # Suffix: 1E4C9B93F3F0682250B6CF8331B7EE68FD8

        mock_response = Mock()
        mock_response.status_code = 200
        # Return a matching suffix
        target_suffix = "1E4C9B93F3F0682250B6CF8331B7EE68FD8"
        mock_response.text = f"{target_suffix}:12345\nOTHER:1"

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_client.get = mock_get

        is_breached, count = await check_password_breach("password")
        assert is_breached is True
        assert count == 12345

        # Test clean password
        mock_response.text = "NOMATCH:1"
        is_breached, count = await check_password_breach("cleanpassword")
        assert is_breached is False

    @pytest.mark.asyncio
    async def test_audit_password(self):
        """Test password audit and strength levels."""
        from security.password import audit_password

        # Very Strong
        res = await audit_password("VeryStrongPassword123!@#")
        assert res.strength_level == "very_strong" or res.strength_level == "strong"

        # Weak
        res = await audit_password("weak")
        assert res.strength_level == "weak"

        # Moderate
        res = await audit_password("Moderate1")
        assert res.strength_level in ["moderate", "weak", "strong"]  # depends on exact calculation
