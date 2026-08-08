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

# Default trusted proxy IPs (loopback and common Docker networks)
DEFAULT_TRUSTED_PROXIES: set[str] = {
    "127.0.0.1",
    "::1",
    "10.0.0.0/8",  # Private network
    "172.16.0.0/12",  # Docker default
    "192.168.0.0/16",  # Private network
}

# Cloud provider proxy ranges (these IPs are typically set by load balancers)
CLOUD_TRUSTED_PROXIES: dict[str, list[str]] = {
    "render": [
        # Render's internal proxy network
        "10.0.0.0/8",
    ],
    "vercel": [
        # Vercel's public edge ranges are not a stable application-owned
        # trust boundary. Configure TRUSTED_PROXIES with the actual proxy
        # addresses for a deployment that terminates requests behind Vercel.
    ],
    "cloudflare": [
        "173.245.48.0/20",
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "141.101.64.0/18",
        "108.162.192.0/18",
        "190.93.240.0/20",
        "188.114.96.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
        "162.158.0.0/15",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "172.64.0.0/13",
        "131.0.72.0/22",
    ],
}


def get_trusted_proxies() -> set[str]:
    """
    Get the set of trusted proxy CIDRs based on environment configuration.

    Environment Variables:
        TRUSTED_PROXIES: Comma-separated list of IP addresses or CIDRs
        CLOUD_PROVIDER: Name of cloud provider (render, vercel, cloudflare)

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

    # Add cloud provider proxies
    cloud_provider = os.getenv("CLOUD_PROVIDER", "").lower()
    if cloud_provider in CLOUD_TRUSTED_PROXIES:
        trusted.update(CLOUD_TRUSTED_PROXIES[cloud_provider])
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
        proxies = trusted_proxies or get_trusted_proxies()
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


def get_client_ip(request: Request, trust_proxy: bool = True) -> str:  # noqa: PLR0911
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
    # Get direct connection IP
    direct_ip = request.client.host if request.client else None

    if not direct_ip:
        return "unknown"

    # Validate direct IP
    direct_ip = validate_ip_address(direct_ip)
    if not direct_ip:
        return "unknown"

    # If not trusting proxies, return direct IP
    if not trust_proxy:
        return direct_ip

    # Check environment - in production, be more careful about trusting headers
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # Check if the direct connection is from a trusted proxy
    # Direct connection is not from a trusted proxy
    # Don't trust X-Forwarded-For in this case
    if not is_trusted_proxy(direct_ip) and environment == "production":
        logger.debug(f"Request not from trusted proxy, using direct IP: {direct_ip}")
        return direct_ip

    # Check X-Forwarded-For header
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Parse the header (format: "client, proxy1, proxy2, ...")
        ips = [ip.strip() for ip in forwarded_for.split(",")]

        # Find the rightmost non-trusted IP (working backwards)
        # This is more secure than taking the leftmost
        trusted_proxies = get_trusted_proxies()

        for ip in reversed(ips):
            validated_ip = validate_ip_address(ip)
            if validated_ip and not is_trusted_proxy(validated_ip, trusted_proxies):
                return validated_ip

        # All IPs in the chain are trusted - take the leftmost (original client)
        if ips:
            first_ip = validate_ip_address(ips[0])
            if first_ip:
                return first_ip

    # Check X-Real-IP header (simpler, often set by nginx)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        validated_real_ip = validate_ip_address(real_ip)
        if validated_real_ip:
            return validated_real_ip

    # Fallback to direct IP
    return direct_ip


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
