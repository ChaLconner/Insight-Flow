from unittest.mock import MagicMock

import pytest
from fastapi import Request

from utils.request_security import (
    DEFAULT_TRUSTED_PROXIES,
    get_client_ip,
    get_request_metadata,
    get_trusted_proxies,
    is_trusted_proxy,
    validate_ip_address,
)


class TestRequestSecurity:
    """Tests for request_security.py."""

    def test_validate_ip_address(self):
        """Test IP validation."""
        assert validate_ip_address("127.0.0.1") == "127.0.0.1"
        assert validate_ip_address("  192.168.1.1  ") == "192.168.1.1"  # Trims whitespace
        assert validate_ip_address("::1") == "::1"  # IPv6

        # Invalid IPs
        assert validate_ip_address("999.999.999.999") is None
        assert validate_ip_address("invalid") is None
        assert validate_ip_address(None) is None
        assert validate_ip_address("text_with_ip_127.0.0.1") is None

        # Injection attempts
        assert validate_ip_address("127.0.0.1; rm -rf /") is None

    def test_is_trusted_proxy(self):
        """Test trusted proxy check."""
        proxies = {"10.0.0.0/8", "127.0.0.1"}

        assert is_trusted_proxy("127.0.0.1", proxies) is True
        assert is_trusted_proxy("10.0.0.50", proxies) is True
        assert is_trusted_proxy("192.168.1.5", proxies) is False
        assert is_trusted_proxy(None, proxies) is False
        assert is_trusted_proxy("invalid", proxies) is False

    @pytest.mark.parametrize(
        "env_var,expected_extra", [("1.1.1.1, 2.2.2.2", {"1.1.1.1", "2.2.2.2"}), ("", set())]
    )
    def test_get_trusted_proxies(self, monkeypatch, env_var, expected_extra):
        """Test loading trusted proxies from env."""
        monkeypatch.setenv("TRUSTED_PROXIES", env_var)
        proxies = get_trusted_proxies()

        for p in DEFAULT_TRUSTED_PROXIES:
            assert p in proxies

        for p in expected_extra:
            assert p in proxies

    def test_get_trusted_proxies_cloud(self, monkeypatch):
        """Test cloud provider proxies."""
        monkeypatch.setenv("CLOUD_PROVIDER", "render")
        monkeypatch.setenv("CLOUD_TRUSTED_PROXIES", "10.0.0.0/8")
        proxies = get_trusted_proxies()
        assert "10.0.0.0/8" in proxies

    def test_get_client_ip_direct(self):
        """Test getting IP from direct connection."""
        request = MagicMock(spec=Request)
        request.client.host = "1.2.3.4"
        request.headers = {}

        assert get_client_ip(request) == "1.2.3.4"

    def test_get_client_ip_x_forwarded_for_trusted(self, monkeypatch):
        """Test X-Forwarded-For when direct connection is trusted."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.0/8")
        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"  # Trusted
        request.headers = {
            "x-forwarded-for": "1.2.3.4, 10.0.0.1"  # 10.0.0.1 is also trusted (private)
        }

        # Should pick 1.2.3.4 (rightmost non-trusted)
        assert get_client_ip(request) == "1.2.3.4"

    def test_get_client_ip_x_forwarded_for_untrusted_dmz(self, monkeypatch):
        """Test X-Forwarded-For when direct connection is Untrusted (e.g. public load balancer)."""
        monkeypatch.setenv(
            "DOCKER_ENV", "production"
        )  # Should check env? No, logic uses TRUSTED check.

        # If accessing directly from public IP, even if header is present, we might return direct IP
        # UNLESS that public IP is configured as trusted (e.g. Cloudflare).

        request = MagicMock(spec=Request)
        request.client.host = "8.8.8.8"  # Untrusted public IP
        request.headers = {"x-forwarded-for": "1.2.3.4"}

        # Case 1: Dev environment (TRUSTS anything by default behavior? No, depends on impl)
        # Impl: if not is_trusted_proxy(direct_ip) and environment == "production": return direct_ip

        monkeypatch.setenv("ENVIRONMENT", "production")
        assert get_client_ip(request) == "8.8.8.8"

        monkeypatch.setenv("ENVIRONMENT", "development")
        # Development must not make client-supplied forwarding headers trusted.
        assert get_client_ip(request) == "8.8.8.8"

    def test_private_peer_does_not_implicitly_trust_forwarded_headers(self, monkeypatch):
        """Private address space is not a proxy trust boundary by itself."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        request = MagicMock(spec=Request)
        request.client.host = "172.20.0.5"
        request.headers = {"x-forwarded-for": "203.0.113.10"}

        assert get_client_ip(request) == "172.20.0.5"

    def test_get_client_ip_x_real_ip(self):
        """Test X-Real-IP fallback."""
        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"
        request.headers = {"x-real-ip": "1.2.3.4"}

        assert get_client_ip(request) == "1.2.3.4"

    def test_get_request_metadata(self):
        """Test metadata extraction."""
        request = MagicMock(spec=Request)
        request.client.host = "1.2.3.4"
        request.headers = {
            "user-agent": "TestAgent",
            "origin": "https://example.com",
            "referer": "https://google.com",
            "x-request-id": "req-123",
        }

        meta = get_request_metadata(request)
        assert meta["client_ip"] == "1.2.3.4"
        assert meta["user_agent"] == "TestAgent"
        assert meta["origin"] == "https://example.com"

    def test_get_client_ip_no_client(self):
        """Test when client info is missing."""
        request = MagicMock(spec=Request)
        request.client = None
        assert get_client_ip(request) == "unknown"

    def test_get_client_ip_no_trust(self):
        """Test explicitly disabling proxy trust."""
        request = MagicMock(spec=Request)
        request.client.host = "1.2.3.4"
        # Even with headers, should verify direct IP
        request.headers = {"x-forwarded-for": "10.0.0.1"}

        ip = get_client_ip(request, trust_proxy=False)
        assert ip == "1.2.3.4"
