from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import Request

from security.token_fingerprint import (
    ClientFingerprint,
    FingerprintStrictness,
    _get_ip_prefix,
    _hash_user_agent,
    extract_fingerprint,
    verify_fingerprint_claim,
)


# Mock utils.request_security.get_client_ip
@pytest.fixture
def mock_get_client_ip():
    with pytest.helpers.mock_module("utils.request_security") as mock:
        mock.get_client_ip = Mock(return_value="127.0.0.1")
        yield mock.get_client_ip


class TestTokenFingerprint:
    """Tests for token fingerprinting module."""

    def test_hash_user_agent(self):
        """Test user agent hashing."""
        ua1 = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        ua2 = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

        hash1 = _hash_user_agent(ua1)
        hash2 = _hash_user_agent(ua2)

        assert hash1 != hash2
        assert len(hash1) == 16

        # Test Case Insensitivity and whitespace
        hash1_noisy = _hash_user_agent("  " + ua1 + "  ")
        hash1_upper = _hash_user_agent(ua1.upper())

        assert hash1_noisy == hash1
        assert hash1_upper == hash1  # Implementation does .lower()

        # Test empty
        assert _hash_user_agent("") == "no_ua"
        assert _hash_user_agent(None) == "no_ua"

    def test_get_ip_prefix_ipv4(self):
        """Test IPv4 prefix extraction with default 2 octets (/16 network)."""
        # Default: 2 octets for mobile-friendly auth
        assert _get_ip_prefix("192.168.1.50") == "192.168"
        assert _get_ip_prefix("10.0.0.1") == "10.0"
        assert _get_ip_prefix("127.0.0.1") == "127.0"
        
        # Explicit 3 octets (/24 network - stricter)
        assert _get_ip_prefix("192.168.1.50", octets=3) == "192.168.1"
        assert _get_ip_prefix("10.0.0.1", octets=3) == "10.0.0"

        # Explicit 1 octet (/8 network - very lenient)
        assert _get_ip_prefix("192.168.1.50", octets=1) == "192"

        # Invalid/Short IPs
        assert _get_ip_prefix("1.2") == "1.2"  # 2 octets matches exactly
        assert _get_ip_prefix("1") is None  # Not enough parts
        assert _get_ip_prefix("unknown") is None
        assert _get_ip_prefix(None) is None

    def test_get_ip_prefix_ipv6(self):
        """Test IPv6 prefix extraction with default 2 segments."""
        # Default: 2 segments
        assert _get_ip_prefix("2001:db8:3333:4444:5555:6666:7777:8888") == "2001:db8"
        
        # Explicit 3 segments
        assert _get_ip_prefix("2001:db8:3333:4444:5555:6666:7777:8888", octets=3) == "2001:db8:3333"
        
        assert (
            _get_ip_prefix("::1") == "127.0"
        )  # Loopback matches 127.0 consistently

    def test_client_fingerprint_string(self):
        """Test fingerprint string representation."""
        fp = ClientFingerprint(
            user_agent_hash="abc1234", ip_prefix="192.168", full_ip="192.168.1.10"
        )

        assert fp.to_string(FingerprintStrictness.LENIENT) == "abc1234"
        assert fp.to_string(FingerprintStrictness.NORMAL) == "abc1234:192.168"
        assert fp.to_string(FingerprintStrictness.STRICT) == "abc1234:192.168.1.10"

        fp_empty = ClientFingerprint(user_agent_hash="abc1234", ip_prefix=None, full_ip=None)
        assert fp_empty.to_string(FingerprintStrictness.NORMAL) == "abc1234:unknown"

    def test_client_fingerprint_matches(self):
        """Test matching logic with /16 network (2 octets)."""
        # Using 2 octets: 10.0.x.x matches 10.0.y.y (same /16 network)
        fp1 = ClientFingerprint("hash1", "10.0", "10.0.0.1")
        fp2 = ClientFingerprint("hash1", "10.0", "10.0.100.2")  # Different IP, same /16 subnet
        fp3 = ClientFingerprint("hash1", "10.1", "10.1.0.1")  # Different /16 subnet
        fp4 = ClientFingerprint("hash2", "10.0", "10.0.0.1")  # Different UA

        # Normal Strictness (Default)
        match, _ = fp1.matches(fp2, FingerprintStrictness.NORMAL)
        assert match is True  # Same /16 subnet

        match, _ = fp1.matches(fp3, FingerprintStrictness.NORMAL)
        assert match is False  # Different /16 subnet

        match, _ = fp1.matches(fp4, FingerprintStrictness.NORMAL)
        assert match is False  # Different UA

        # Strict Strictness
        match, _ = fp1.matches(fp2, FingerprintStrictness.STRICT)
        assert match is False  # Different IP

        # Lenient Strictness
        match, _ = fp1.matches(fp3, FingerprintStrictness.LENIENT)
        assert match is True  # UA matches, ignore IP

    @patch("security.token_fingerprint.extract_fingerprint")
    def test_verify_fingerprint_claim(self, mock_extract):
        """Test verification logic with /16 network."""
        # Setup mock request
        request = MagicMock(spec=Request)

        # Test Case 1: Match (same /16 network)
        mock_extract.return_value = ClientFingerprint("hash1", "10.0", "10.0.0.1")

        stored_fp = "hash1:10.0"  # Normal format with 2 octets

        valid, reason = verify_fingerprint_claim(request, stored_fp, FingerprintStrictness.NORMAL)
        assert valid is True
        assert reason == "match"

        # Test Case 2: No stored fingerprint
        valid, reason = verify_fingerprint_claim(request, None)
        assert valid is True
        assert reason == "no_fingerprint_stored"

        # Test Case 3: UA Mismatch (Normal)
        mock_extract.return_value = ClientFingerprint("hash2", "10.0", "10.0.0.1")
        valid, reason = verify_fingerprint_claim(request, stored_fp, FingerprintStrictness.NORMAL)
        assert valid is False
        assert reason == "user_agent_mismatch"

        # Test Case 4: IP Mismatch (Normal) - different /16 network
        mock_extract.return_value = ClientFingerprint("hash1", "10.1", "10.1.0.1")
        valid, reason = verify_fingerprint_claim(request, stored_fp, FingerprintStrictness.NORMAL)
        assert valid is False
        assert reason == "ip_network_mismatch"

        # Test Case 5: Lenient Mode
        mock_extract.return_value = ClientFingerprint(
            "hash2", "10.0.0", "10.0.0.1"
        )  # Explicitly set distinct hash
        stored_fp_lenient = "hash1"
        valid, reason = verify_fingerprint_claim(
            request, stored_fp_lenient, FingerprintStrictness.LENIENT
        )
        assert valid is False  # Because hash2 (from prev step setup) != hash1

        # Correct hash for lenient
        mock_extract.return_value = ClientFingerprint("hash1", "10.1", "10.1.0.1")
        valid, reason = verify_fingerprint_claim(
            request, stored_fp_lenient, FingerprintStrictness.LENIENT
        )
        assert valid is True

    def test_extract_fingerprint(self):
        """Test extraction from request with 2 octets default."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "TestAgent"}

        with patch("utils.request_security.get_client_ip", return_value="192.168.1.100"):
            fp = extract_fingerprint(request)

            assert fp.user_agent_hash == _hash_user_agent("TestAgent")
            assert fp.ip_prefix == "192.168"  # 2 octets now
            assert fp.full_ip == "192.168.1.100"

    def test_mobile_friendly_ip_matching(self):
        """Test that IP changes within same /16 network are accepted.
        
        This is the key improvement for mobile users whose ISP may rotate
        their IP within the same network block.
        """
        # Scenario: User's IP changes from 171.4.248.x to 171.4.217.x
        # With /24 (3 octets): This would FAIL
        # With /16 (2 octets): This should PASS ✓
        
        fp_prefix_16 = _get_ip_prefix("171.4.248.50", octets=2)
        fp2_prefix_16 = _get_ip_prefix("171.4.217.38", octets=2)
        assert fp_prefix_16 == fp2_prefix_16 == "171.4"  # Same /16 network
        
        # But with /24 they would differ
        fp_prefix_24 = _get_ip_prefix("171.4.248.50", octets=3)
        fp2_prefix_24 = _get_ip_prefix("171.4.217.38", octets=3)
        assert fp_prefix_24 == "171.4.248"
        assert fp2_prefix_24 == "171.4.217"
        assert fp_prefix_24 != fp2_prefix_24  # Different /24 networks
