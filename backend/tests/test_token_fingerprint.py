
import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi import Request
from security.token_fingerprint import (
    ClientFingerprint,
    FingerprintStrictness,
    extract_fingerprint,
    generate_fingerprint_claim,
    verify_fingerprint_claim,
    _hash_user_agent,
    _get_ip_prefix,
    DEFAULT_STRICTNESS
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
        assert hash1_upper == hash1 # Implementation does .lower()
        
        # Test empty
        assert _hash_user_agent("") == "no_ua"
        assert _hash_user_agent(None) == "no_ua"

    def test_get_ip_prefix_ipv4(self):
        """Test IPv4 prefix extraction."""
        assert _get_ip_prefix("192.168.1.50") == "192.168.1"
        assert _get_ip_prefix("10.0.0.1") == "10.0.0"
        assert _get_ip_prefix("127.0.0.1") == "127.0.0"
        
        # Invalid/Short IPs
        assert _get_ip_prefix("1.2") is None # Not enough parts
        assert _get_ip_prefix("unknown") is None
        assert _get_ip_prefix(None) is None

    def test_get_ip_prefix_ipv6(self):
        """Test IPv6 prefix extraction."""
        assert _get_ip_prefix("2001:db8:3333:4444:5555:6666:7777:8888") == "2001:db8:3333"
        assert _get_ip_prefix("::1") == "::1" # Too short for /48 logic with simple split, returns as is

    def test_client_fingerprint_string(self):
        """Test fingerprint string representation."""
        fp = ClientFingerprint(
            user_agent_hash="abc1234",
            ip_prefix="192.168.1",
            full_ip="192.168.1.10"
        )
        
        assert fp.to_string(FingerprintStrictness.LENIENT) == "abc1234"
        assert fp.to_string(FingerprintStrictness.NORMAL) == "abc1234:192.168.1"
        assert fp.to_string(FingerprintStrictness.STRICT) == "abc1234:192.168.1.10"

        fp_empty = ClientFingerprint(
            user_agent_hash="abc1234",
            ip_prefix=None,
            full_ip=None
        )
        assert fp_empty.to_string(FingerprintStrictness.NORMAL) == "abc1234:unknown"

    def test_client_fingerprint_matches(self):
        """Test matching logic."""
        fp1 = ClientFingerprint("hash1", "10.0.0", "10.0.0.1")
        fp2 = ClientFingerprint("hash1", "10.0.0", "10.0.0.2") # Different IP, same subnet
        fp3 = ClientFingerprint("hash1", "10.0.1", "10.0.1.1") # Different subnet
        fp4 = ClientFingerprint("hash2", "10.0.0", "10.0.0.1") # Different UA

        # Normal Strictness (Default)
        match, _ = fp1.matches(fp2, FingerprintStrictness.NORMAL)
        assert match is True # Same subnet

        match, _ = fp1.matches(fp3, FingerprintStrictness.NORMAL)
        assert match is False # Different subnet

        match, _ = fp1.matches(fp4, FingerprintStrictness.NORMAL)
        assert match is False # Different UA

        # Strict Strictness
        match, _ = fp1.matches(fp2, FingerprintStrictness.STRICT)
        assert match is False # Different IP

        # Lenient Strictness
        match, _ = fp1.matches(fp3, FingerprintStrictness.LENIENT)
        assert match is True # UA matches, ignore IP

    @patch("security.token_fingerprint.extract_fingerprint")
    def test_verify_fingerprint_claim(self, mock_extract):
        """Test verification logic."""
        # Setup mock request
        request = MagicMock(spec=Request)
        
        # Test Case 1: Match
        mock_extract.return_value = ClientFingerprint("hash1", "10.0.0", "10.0.0.1")
        
        stored_fp = "hash1:10.0.0" # Normal format
        
        valid, reason = verify_fingerprint_claim(request, stored_fp, FingerprintStrictness.NORMAL)
        assert valid is True
        assert reason == "match"
        
        # Test Case 2: No stored fingerprint
        valid, reason = verify_fingerprint_claim(request, None)
        assert valid is True
        assert reason == "no_fingerprint_stored"
        
        # Test Case 3: UA Mismatch (Normal)
        mock_extract.return_value = ClientFingerprint("hash2", "10.0.0", "10.0.0.1")
        valid, reason = verify_fingerprint_claim(request, stored_fp, FingerprintStrictness.NORMAL)
        assert valid is False
        assert reason == "user_agent_mismatch"

        # Test Case 4: IP Mismatch (Normal)
        mock_extract.return_value = ClientFingerprint("hash1", "10.0.1", "10.0.1.1")
        valid, reason = verify_fingerprint_claim(request, stored_fp, FingerprintStrictness.NORMAL)
        assert valid is False
        assert reason == "ip_network_mismatch"

        # Test Case 5: Lenient Mode
        mock_extract.return_value = ClientFingerprint("hash2", "10.0.0", "10.0.0.1") # Explicitly set distinct hash
        stored_fp_lenient = "hash1"
        valid, reason = verify_fingerprint_claim(request, stored_fp_lenient, FingerprintStrictness.LENIENT)
        assert valid is False # Because hash2 (from prev step setup) != hash1
        
        # Correct hash for lenient
        mock_extract.return_value = ClientFingerprint("hash1", "10.0.1", "10.0.1.1")
        valid, reason = verify_fingerprint_claim(request, stored_fp_lenient, FingerprintStrictness.LENIENT)
        assert valid is True

    def test_extract_fingerprint(self):
        """Test extraction from request."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "TestAgent"}
        
        with patch("utils.request_security.get_client_ip", return_value="192.168.1.100"):
            fp = extract_fingerprint(request)
            
            assert fp.user_agent_hash == _hash_user_agent("TestAgent")
            assert fp.ip_prefix == "192.168.1"
            assert fp.full_ip == "192.168.1.100"

