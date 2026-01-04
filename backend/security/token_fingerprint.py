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
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    pass

logger = logging.getLogger("token_fingerprint")


class FingerprintStrictness(str, Enum):
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
    ip_prefix: str | None  # First 3 octets of IPv4 or /48 of IPv6
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
        strictness: FingerprintStrictness = FingerprintStrictness.NORMAL
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
            if self.ip_prefix and other.ip_prefix:
                if self.ip_prefix != other.ip_prefix:
                    return False, "ip_network_mismatch"
            return True, "match"
        
        # Check full IP for STRICT mode
        if strictness == FingerprintStrictness.STRICT:
            if self.full_ip != other.full_ip:
                return False, "ip_exact_mismatch"
            return True, "match"
        
        return True, "match"


def _hash_user_agent(user_agent: str | None) -> str:
    """Create SHA256 hash of User-Agent string."""
    if not user_agent:
        return "no_ua"
    
    # Normalize: lowercase and strip
    normalized = user_agent.lower().strip()
    
    # Hash for privacy
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _get_ip_prefix(ip: str | None) -> str | None:
    """
    Extract network prefix from IP address.
    
    IPv4: First 3 octets (e.g., 192.168.1.xxx -> 192.168.1)
    IPv6: First 48 bits (e.g., 2001:db8:1234:: /48)
    """
    if not ip or ip == "unknown":
        return None
    
    try:
        if ":" in ip:
            # IPv6: Take first 3 segments (/48)
            parts = ip.split(":")
            return ":".join(parts[:3])
        else:
            # IPv4: Take first 3 octets
            parts = ip.split(".")
            if len(parts) >= 3:
                return ".".join(parts[:3])
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
    
    # Simple string comparison for NORMAL mode
    if strictness == FingerprintStrictness.NORMAL:
        if current_fp_string == stored_fingerprint:
            return True, "match"
        
        # More detailed mismatch analysis
        stored_parts = stored_fingerprint.split(":", 1)
        current_parts = current_fp_string.split(":", 1)
        
        if len(stored_parts) >= 1 and len(current_parts) >= 1:
            if stored_parts[0] != current_parts[0]:
                logger.warning(
                    f"Token fingerprint mismatch: User-Agent changed. "
                    f"Stored: {stored_parts[0][:8]}..., Current: {current_parts[0][:8]}..."
                )
                return False, "user_agent_mismatch"
            
            if len(stored_parts) > 1 and len(current_parts) > 1:
                if stored_parts[1] != current_parts[1]:
                    logger.warning(
                        f"Token fingerprint mismatch: IP network changed. "
                        f"Stored: {stored_parts[1]}, Current: {current_parts[1]}"
                    )
                    return False, "ip_network_mismatch"
        
        return False, "fingerprint_mismatch"
    
    # LENIENT mode - only check UA hash
    elif strictness == FingerprintStrictness.LENIENT:
        stored_ua = stored_fingerprint.split(":")[0] if ":" in stored_fingerprint else stored_fingerprint
        if current_fp.user_agent_hash == stored_ua:
            return True, "match"
        return False, "user_agent_mismatch"
    
    # STRICT mode
    else:
        if current_fp_string == stored_fingerprint:
            return True, "match"
        return False, "strict_mismatch"


# Configuration - can be changed via environment variable
import os

_strictness_str = os.getenv("TOKEN_FINGERPRINT_STRICTNESS", "normal").lower()
if _strictness_str == "lenient":
    DEFAULT_STRICTNESS = FingerprintStrictness.LENIENT
elif _strictness_str == "strict":
    DEFAULT_STRICTNESS = FingerprintStrictness.STRICT
else:
    DEFAULT_STRICTNESS = FingerprintStrictness.NORMAL

# Feature flag
FINGERPRINT_ENABLED = os.getenv("TOKEN_FINGERPRINT_ENABLED", "true").lower() == "true"
