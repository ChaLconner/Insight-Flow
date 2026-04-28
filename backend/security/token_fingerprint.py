"""
Token Fingerprint Module - A+ Security Enhancement.

Provides device fingerprinting for token binding to prevent token theft.
Tokens are bound to specific client characteristics (User-Agent, IP range).

Security Features:
- Token stolen from different browser/device will be rejected
- Configurable strictness levels
- Graceful fallback on fingerprint mismatch
"""

import hashlib
import ipaddress
import logging
import os
from dataclasses import dataclass
from enum import StrEnum

from fastapi import Request

logger = logging.getLogger("token_fingerprint")

# =============================================================================
# Configuration - can be changed via environment variables
# =============================================================================

# IP prefix configuration - /16 network (2 octets) is best practice for mobile users
# This allows users to stay authenticated even if their ISP rotates their IP within the same network
# Examples:
#   - 2 octets (/16): 171.4.248.x and 171.4.217.x both match as "171.4" ✓ (recommended)
#   - 3 octets (/24): 171.4.248.x != 171.4.217.x (too strict for mobile)
#   - 1 octet (/8):   171.x.x.x (too lenient, not recommended)
IP_PREFIX_OCTETS = int(os.getenv("TOKEN_IP_PREFIX_OCTETS", "2"))


class FingerprintStrictness(StrEnum):
    """Fingerprint verification strictness levels."""

    # Only validate User-Agent (most lenient, allows mobile network IP changes)
    LENIENT = "lenient"

    # Validate User-Agent + IP network prefix (recommended for most apps)
    NORMAL = "normal"

    # Validate full fingerprint including exact IP (most strict)
    STRICT = "strict"


@dataclass
class ClientFingerprint:
    """Client device fingerprint data."""

    user_agent_hash: str  # SHA256 of User-Agent (privacy-preserving)
    ip_prefix: str | None  # First N octets of IPv4 (configurable, default /16)
    full_ip: str | None  # Full IP address (only used in strict mode)

    def to_string(self, strictness: FingerprintStrictness = FingerprintStrictness.NORMAL) -> str:
        """Generate fingerprint string based on strictness level."""
        if strictness == FingerprintStrictness.LENIENT:
            return self.user_agent_hash
        elif strictness == FingerprintStrictness.NORMAL:
            return f"{self.user_agent_hash}:{self.ip_prefix or 'unknown'}"
        else:  # STRICT
            return f"{self.user_agent_hash}:{self.full_ip or 'unknown'}"

    def matches(
        self,
        other: "ClientFingerprint",
        strictness: FingerprintStrictness = FingerprintStrictness.NORMAL,
    ) -> tuple[bool, str]:
        """
        Check if this fingerprint matches another.

        Returns:
            Tuple of (matches: bool, reason: str)
        """
        # Always check User-Agent hash
        if self.user_agent_hash != other.user_agent_hash:
            return False, "user_agent_mismatch"

        if strictness == FingerprintStrictness.LENIENT:
            return True, "match"

        # Check IP prefix for NORMAL mode
        if strictness == FingerprintStrictness.NORMAL:
            if self.ip_prefix and other.ip_prefix and self.ip_prefix != other.ip_prefix:
                return False, "ip_network_mismatch"
            return True, "match"

        # Check full IP for STRICT mode
        if strictness == FingerprintStrictness.STRICT:
            if self.full_ip != other.full_ip:
                return False, "ip_exact_mismatch"
            return True, "match"

        # return True, "match"  # Unreachable if Enum is exhaustive


def _hash_user_agent(user_agent: str | None) -> str:
    """Create SHA256 hash of User-Agent string."""
    if not user_agent:
        return "no_ua"

    # Normalize: lowercase and strip
    normalized = user_agent.lower().strip()

    # Hash for privacy
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _get_ip_prefix(ip: str | None, octets: int | None = None) -> str | None:
    """
    Extract network prefix from IP address.

    IPv4: First N octets (configurable via IP_PREFIX_OCTETS, default 2 for /16 network)
          This is best practice for mobile users who may have IP changes within same ISP network.
          Example: 171.4.248.x and 171.4.217.x will both match as "171.4"
    IPv6: First N segments (default 2 for /32)

    Args:
        ip: IP address string
        octets: Number of octets to use (None = use IP_PREFIX_OCTETS env var)
    """
    if not ip or ip == "unknown":
        return None

    try:
        # Check for loopback/localhost addresses
        # This handles the case where simple string splitting produces different
        # prefixes for 127.0.0.1 and ::1, which often switch on localhost
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_loopback:
            return "127.0"  # Consistent prefix for all local traffic
    except ValueError:
        pass

    # Use configured octets or default (2 for /16 - mobile friendly)
    num_octets = octets if octets is not None else IP_PREFIX_OCTETS

    try:
        if ":" in ip:
            # IPv6: Take first N segments
            parts = ip.split(":")
            return ":".join(parts[:num_octets])
        else:
            # IPv4: Take first N octets
            parts = ip.split(".")
            if len(parts) >= num_octets:
                return ".".join(parts[:num_octets])
    except Exception:
        pass

    return None


def extract_fingerprint(request: Request) -> ClientFingerprint:
    """
    Extract client fingerprint from a request.

    Args:
        request: FastAPI Request object

    Returns:
        ClientFingerprint with device/network characteristics
    """
    from utils.request_security import get_client_ip

    # Get User-Agent
    user_agent = request.headers.get("user-agent", "")
    ua_hash = _hash_user_agent(user_agent)

    # Get client IP
    client_ip = get_client_ip(request)
    ip_prefix = _get_ip_prefix(client_ip)

    return ClientFingerprint(
        user_agent_hash=ua_hash,
        ip_prefix=ip_prefix,
        full_ip=client_ip if client_ip != "unknown" else None,
    )


def generate_fingerprint_claim(request: Request) -> str:
    """
    Generate a fingerprint claim to include in JWT token.

    Usage:
        fingerprint = generate_fingerprint_claim(request)
        token = create_access_token(data={"sub": user_id, "fp": fingerprint})
    """
    fp = extract_fingerprint(request)
    return fp.to_string(FingerprintStrictness.NORMAL)


def verify_fingerprint_claim(
    request: Request,
    stored_fingerprint: str | None,
    strictness: FingerprintStrictness = FingerprintStrictness.NORMAL,
) -> tuple[bool, str]:
    """
    Verify that the current request matches the fingerprint stored in the token.

    Args:
        request: Current FastAPI Request
        stored_fingerprint: Fingerprint string from JWT token ('fp' claim)
        strictness: How strictly to verify

    Returns:
        Tuple of (is_valid: bool, reason: str)
    """
    # No fingerprint stored - allow (backwards compatibility)
    if not stored_fingerprint:
        logger.debug("No fingerprint in token, allowing request (legacy token)")
        return True, "no_fingerprint_stored"

    # Extract current fingerprint
    current_fp = extract_fingerprint(request)
    current_fp_string = current_fp.to_string(strictness)

    # 1. Exact match check (fastest and most common case)
    if current_fp_string == stored_fingerprint:
        return True, "match"

    result = (False, "fingerprint_mismatch")

    # 2. LENIENT mode - only check UA hash
    if strictness == FingerprintStrictness.LENIENT:
        stored_ua = (
            stored_fingerprint.split(":")[0] if ":" in stored_fingerprint else stored_fingerprint
        )
        if current_fp.user_agent_hash == stored_ua:
            result = (True, "match")
        else:
            result = (False, "user_agent_mismatch")

    # 3. STRICT mode - exact match required (already checked above)
    elif strictness == FingerprintStrictness.STRICT:
        result = (False, "strict_mismatch")

    # 4. NORMAL mode - Detailed mismatch analysis
    else:
        stored_parts = stored_fingerprint.split(":", 1)
        current_parts = current_fp_string.split(":", 1)

        has_ua = len(stored_parts) >= 1 and len(current_parts) >= 1
        has_ip = len(stored_parts) > 1 and len(current_parts) > 1

        if has_ua and stored_parts[0] != current_parts[0]:
            logger.warning(
                f"Token fingerprint mismatch: User-Agent changed. "
                f"Stored: {stored_parts[0][:8]}..., Current: {current_parts[0][:8]}..."
            )
            result = (False, "user_agent_mismatch")
        elif has_ip and stored_parts[1] != current_parts[1]:
            logger.warning(
                f"Token fingerprint mismatch: IP network changed. "
                f"Stored: {stored_parts[1]}, Current: {current_parts[1]}"
            )
            result = (False, "ip_network_mismatch")

    return result


# Strictness configuration
_strictness_str = os.getenv("TOKEN_FINGERPRINT_STRICTNESS", "normal").lower()
if _strictness_str == "lenient":
    DEFAULT_STRICTNESS = FingerprintStrictness.LENIENT
elif _strictness_str == "strict":
    DEFAULT_STRICTNESS = FingerprintStrictness.STRICT
else:
    DEFAULT_STRICTNESS = FingerprintStrictness.NORMAL

# Feature flag to enable/disable fingerprinting
FINGERPRINT_ENABLED = os.getenv("TOKEN_FINGERPRINT_ENABLED", "true").lower() == "true"
