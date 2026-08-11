"""
Request Security Utilities.
Provides secure methods for extracting client information from requests.

Security Features:
- Trusted proxy validation for X-Forwarded-For headers
- IP address validation and sanitization
- Protection against IP spoofing attacks
"""

import ipaddress
import os
import re
from typing import Any

from fastapi import Request

from utils.logger import setup_logger

logger = setup_logger("request_security")

# =============================================================================
# Trusted Proxy Configuration
# =============================================================================

# Only loopback is trusted by default. Deployment-specific proxy addresses
# must be configured explicitly with TRUSTED_PROXIES.
DEFAULT_TRUSTED_PROXIES: set[str] = {
    "127.0.0.1",
    "::1",
}


def get_trusted_proxies() -> set[str]:
    """
    Get the set of trusted proxy CIDRs based on environment configuration.

    Environment Variables:
        TRUSTED_PROXIES: Comma-separated list of IP addresses or CIDRs
        CLOUD_PROVIDER: Optional deployment provider label for logging
        CLOUD_TRUSTED_PROXIES: Comma-separated provider proxy IPs or CIDRs

    Returns:
        Set of trusted proxy IPs/CIDRs
    """
    trusted = DEFAULT_TRUSTED_PROXIES.copy()

    # Add custom trusted proxies from environment
    custom_proxies = os.getenv("TRUSTED_PROXIES", "")
    if custom_proxies:
        for proxy in custom_proxies.split(","):
            proxy = proxy.strip()
            if proxy:
                trusted.add(proxy)

    # Add provider proxies only when explicitly configured by the operator.
    cloud_provider = os.getenv("CLOUD_PROVIDER", "").lower()
    cloud_proxies = os.getenv("CLOUD_TRUSTED_PROXIES", "")
    if cloud_provider and cloud_proxies:
        trusted.update(proxy.strip() for proxy in cloud_proxies.split(",") if proxy.strip())
        logger.debug(f"Added {cloud_provider} trusted proxies")

    return trusted


def is_trusted_proxy(ip: str, trusted_proxies: set[str] | None = None) -> bool:
    """
    Check if an IP address is from a trusted proxy.

    Args:
        ip: IP address to check
        trusted_proxies: Optional set of trusted IPs/CIDRs (defaults to get_trusted_proxies())

    Returns:
        True if IP is trusted
    """
    if not ip or ip == "unknown":
        return False

    try:
        proxies = trusted_proxies if trusted_proxies is not None else get_trusted_proxies()
        ip_obj = ipaddress.ip_address(ip)

        for proxy in proxies:
            try:
                # Check if it's a network (CIDR) or single IP
                if "/" in proxy:
                    network = ipaddress.ip_network(proxy, strict=False)
                    if ip_obj in network:
                        return True
                elif ip_obj == ipaddress.ip_address(proxy):
                    return True
            except ValueError:
                continue

        return False
    except ValueError:
        logger.warning(f"Invalid IP address format: {ip}")
        return False


def validate_ip_address(ip: str) -> str | None:
    """
    Validate and sanitize an IP address.

    Args:
        ip: IP address string to validate

    Returns:
        Sanitized IP address or None if invalid
    """
    if not ip:
        return None

    # Remove any whitespace
    ip = ip.strip()

    # Basic format validation (prevent injection)
    if not re.match(r"^[\d.:a-fA-F]+$", ip):
        logger.warning(f"IP address contains invalid characters: {ip[:50]}")
        return None

    try:
        # Parse and normalize the IP
        ip_obj = ipaddress.ip_address(ip)
        return str(ip_obj)
    except ValueError:
        logger.warning(f"Invalid IP address: {ip[:50]}")
        return None


def _get_direct_client_ip(request: Request) -> str | None:
    """Extract and validate the address of the direct peer."""
    direct_ip = request.client.host if request.client else None
    if not direct_ip:
        return None
    return validate_ip_address(direct_ip)


def _get_forwarded_client_ip(request: Request) -> str | None:
    """Extract the first untrusted address from a trusted proxy chain."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        return None

    ips = [ip.strip() for ip in forwarded_for.split(",")]
    trusted_proxies = get_trusted_proxies()
    for ip in reversed(ips):
        validated_ip = validate_ip_address(ip)
        if validated_ip and not is_trusted_proxy(validated_ip, trusted_proxies):
            return validated_ip

    if ips:
        return validate_ip_address(ips[0])
    return None


def _get_real_client_ip(request: Request) -> str | None:
    """Extract and validate the simpler X-Real-IP fallback header."""
    real_ip = request.headers.get("x-real-ip")
    if not real_ip:
        return None
    return validate_ip_address(real_ip)


def get_client_ip(request: Request, trust_proxy: bool = True) -> str:
    """
    Extract the real client IP address from a request, handling proxies securely.

    Security considerations:
    - X-Forwarded-For can be spoofed by clients
    - Only trust X-Forwarded-For if request comes from a trusted proxy
    - Take the leftmost IP that's not from a trusted proxy

    Args:
        request: FastAPI Request object
        trust_proxy: Whether to trust X-Forwarded-For headers (default: True)

    Returns:
        Client IP address (or "unknown" if cannot be determined)
    """
    direct_ip = _get_direct_client_ip(request)
    if not direct_ip:
        return "unknown"

    # If not trusting proxies, return direct IP
    if not trust_proxy:
        return direct_ip

    # Forwarding headers are untrusted unless the immediate peer is an
    # explicitly configured proxy. Development mode must not weaken this
    # boundary because clients can still send arbitrary headers locally.
    if not is_trusted_proxy(direct_ip):
        logger.debug(f"Request not from trusted proxy, using direct IP: {direct_ip}")
        return direct_ip

    return _get_forwarded_client_ip(request) or _get_real_client_ip(request) or direct_ip


def get_request_metadata(request: Request) -> dict[str, Any]:
    """
    Extract security-relevant metadata from a request.

    Args:
        request: FastAPI Request object

    Returns:
        Dictionary with client IP, user agent, and other metadata
    """
    return {
        "client_ip": get_client_ip(request),
        "user_agent": request.headers.get("user-agent", "unknown")[:500],  # Limit length
        "origin": request.headers.get("origin"),
        "referer": request.headers.get("referer"),
        "request_id": request.headers.get("x-request-id"),
    }
