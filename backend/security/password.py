"""
Advanced Password Security Module - Staff/Principal Level

Provides:
- Argon2id hashing (PHC winner, memory-hard)
- Have I Been Pwned breach detection (k-Anonymity)
- Progressive password rehashing (bcrypt → argon2)
- Password policy validation with entropy checks
- Context-aware password restrictions
"""

import hashlib
import logging
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
from passlib.context import CryptContext

# Use standard logging to avoid circular import with utils.logger
logger = logging.getLogger("password_security")


# =============================================================================
# Password Hashing with Argon2id + bcrypt fallback
# =============================================================================

# Argon2id configuration (OWASP recommendations)
# - time_cost: 3 iterations
# - memory_cost: 65536 KB (64 MB)
# - parallelism: 4 threads
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated=["bcrypt"],  # Migrate bcrypt hashes to argon2
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
    argon2__hash_len=32,
    argon2__salt_len=16,
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id (PHC winner)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification failed: {e}")
        return False


def verify_and_rehash(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """
    Verify password and upgrade hash algorithm if needed.

    Returns:
        tuple[bool, str | None]: (is_valid, new_hash_if_upgraded)

    Usage:
        is_valid, new_hash = verify_and_rehash(password, user.hashed_password)
        if is_valid and new_hash:
            user.hashed_password = new_hash
            await session.commit()
    """
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)

        if not is_valid:
            return False, None

        # Check if hash needs upgrade (e.g., bcrypt → argon2)
        if pwd_context.needs_update(hashed_password):
            new_hash = pwd_context.hash(plain_password)
            logger.info("Password hash upgraded from bcrypt to argon2id")
            return True, new_hash

        return True, None

    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False, None


def needs_rehash(hashed_password: str) -> bool:
    """Check if a password hash should be upgraded."""
    return pwd_context.needs_update(hashed_password)


def get_hash_algorithm(hashed_password: str) -> str:
    """Identify the algorithm used for a password hash."""
    if hashed_password.startswith("$argon2"):
        return "argon2id"
    elif hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        return "bcrypt"
    return "unknown"


# =============================================================================
# Have I Been Pwned (HIBP) Breach Detection
# =============================================================================


async def check_password_breach(password: str, timeout: float = 2.0) -> tuple[bool, int]:
    """
    Check if password has been exposed in known data breaches.

    Uses Have I Been Pwned API with k-Anonymity (only sends first 5 chars of SHA1).

    Args:
        password: Password to check
        timeout: API timeout in seconds

    Returns:
        tuple[bool, int]: (is_breached, breach_count)

    Reference:
        https://haveibeenpwned.com/API/v3#PwnedPasswords
    """
    try:
        # Create SHA1 hash of password
        sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1_hash[:5], sha1_hash[5:]

        # Query HIBP API with hash prefix (k-Anonymity)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"Add-Padding": "true"},  # Padding to prevent timing attacks
                timeout=timeout,
            )

            if response.status_code != 200:
                logger.warning(f"HIBP API returned status {response.status_code}")
                return False, 0

            # Check if suffix exists in response
            for line in response.text.splitlines():
                hash_suffix, count = line.split(":")
                if hash_suffix == suffix:
                    breach_count = int(count)
                    logger.warning(f"Password found in {breach_count} breaches (HIBP)")
                    return True, breach_count

            return False, 0

    except httpx.TimeoutException:
        logger.warning("HIBP API timeout - skipping breach check")
        return False, 0
    except Exception as e:
        logger.error(f"HIBP check failed: {e}")
        return False, 0


def check_password_breach_sync(password: str) -> tuple[bool, int]:
    """
    Synchronous version of breach check (for non-async contexts).

    Note: Prefer async version when possible for better performance.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
        # If we're already in an async context, we can't use run_until_complete
        logger.warning("Use async check_password_breach in async contexts")
        return False, 0
    except RuntimeError:
        # No running loop, safe to create one
        return asyncio.run(check_password_breach(password))


# =============================================================================
# Password Entropy Calculation
# =============================================================================


class CharacterClass(Enum):
    """Character classes for entropy calculation."""

    LOWERCASE = 26
    UPPERCASE = 26
    DIGITS = 10
    SPECIAL = 32
    EXTENDED = 128


def calculate_entropy(password: str) -> float:
    """
    Calculate password entropy in bits.

    Entropy = log2(character_space ^ length)

    A password with 80+ bits is considered very strong.
    60-80 bits is strong, 40-60 is moderate, <40 is weak.
    """
    if not password:
        return 0.0

    # Determine character space
    char_space = 0

    if re.search(r"[a-z]", password):
        char_space += CharacterClass.LOWERCASE.value
    if re.search(r"[A-Z]", password):
        char_space += CharacterClass.UPPERCASE.value
    if re.search(r"\d", password):
        char_space += CharacterClass.DIGITS.value
    if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        char_space += CharacterClass.SPECIAL.value
    if re.search(r"[^\x00-\x7F]", password):  # Non-ASCII
        char_space += CharacterClass.EXTENDED.value

    if char_space == 0:
        return 0.0

    # Entropy = log2(char_space^length) = length * log2(char_space)
    entropy = len(password) * math.log2(char_space)

    return round(entropy, 2)


# =============================================================================
# Password Policy Engine
# =============================================================================


@dataclass
class PasswordPolicyConfig:
    """Configuration for password policy validation."""

    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    min_entropy_bits: float = 50.0
    check_breached: bool = True
    banned_patterns: list[str] = field(
        default_factory=lambda: [
            r"password",
            r"123456",
            r"qwerty",
            r"admin",
            r"letmein",
            r"welcome",
            r"monkey",
            r"dragon",
        ]
    )
    max_consecutive_chars: int = 3
    block_context_words: bool = True  # Block username/email in password


class PasswordPolicyViolation(Enum):
    """Password policy violation types."""

    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    NO_UPPERCASE = "no_uppercase"
    NO_LOWERCASE = "no_lowercase"
    NO_DIGIT = "no_digit"
    NO_SPECIAL = "no_special"
    LOW_ENTROPY = "low_entropy"
    BREACHED = "breached"
    BANNED_PATTERN = "banned_pattern"
    CONSECUTIVE_CHARS = "consecutive_chars"
    CONTEXT_WORD = "contains_context_word"


@dataclass
class PolicyViolation:
    """Details about a password policy violation."""

    violation_type: PasswordPolicyViolation
    message: str
    severity: str = "error"  # "error" or "warning"


class PasswordPolicy:
    """
    Password policy validation engine.

    Usage:
        policy = PasswordPolicy()
        violations = await policy.validate(
            password="weakpass",
            user_context={"username": "john", "email": "john@example.com"}
        )

        if violations:
            for v in violations:
                print(f"{v.severity}: {v.message}")
    """

    def __init__(self, config: PasswordPolicyConfig | None = None):
        self.config = config or PasswordPolicyConfig()

    async def validate(  # noqa: PLR0912
        self,
        password: str,
        user_context: dict[str, Any] | None = None,
        check_breach: bool | None = None,
    ) -> list[PolicyViolation]:
        """
        Validate password against policy rules.

        Args:
            password: Password to validate
            user_context: Dict with user info (username, email, first_name, etc.)
            check_breach: Override config's breach check setting

        Returns:
            List of policy violations (empty if password is valid)
        """
        violations: list[PolicyViolation] = []
        user_context = user_context or {}

        # Length checks
        if len(password) < self.config.min_length:
            violations.append(
                PolicyViolation(
                    PasswordPolicyViolation.TOO_SHORT,
                    f"Password must be at least {self.config.min_length} characters",
                )
            )

        if len(password) > self.config.max_length:
            violations.append(
                PolicyViolation(
                    PasswordPolicyViolation.TOO_LONG,
                    f"Password must not exceed {self.config.max_length} characters",
                )
            )

        # Character class checks
        if self.config.require_uppercase and not re.search(r"[A-Z]", password):
            violations.append(
                PolicyViolation(
                    PasswordPolicyViolation.NO_UPPERCASE,
                    "Password must contain at least one uppercase letter",
                )
            )

        if self.config.require_lowercase and not re.search(r"[a-z]", password):
            violations.append(
                PolicyViolation(
                    PasswordPolicyViolation.NO_LOWERCASE,
                    "Password must contain at least one lowercase letter",
                )
            )

        if self.config.require_digit and not re.search(r"\d", password):
            violations.append(
                PolicyViolation(
                    PasswordPolicyViolation.NO_DIGIT,
                    "Password must contain at least one digit",
                )
            )

        if self.config.require_special and not re.search(
            r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password
        ):
            violations.append(
                PolicyViolation(
                    PasswordPolicyViolation.NO_SPECIAL,
                    "Password must contain at least one special character",
                )
            )

        # Entropy check
        entropy = calculate_entropy(password)
        if entropy < self.config.min_entropy_bits:
            violations.append(
                PolicyViolation(
                    PasswordPolicyViolation.LOW_ENTROPY,
                    f"Password is too predictable (entropy: {entropy:.0f} bits, "
                    f"minimum: {self.config.min_entropy_bits:.0f} bits)",
                    severity="warning",
                )
            )

        # Consecutive character check
        if self.config.max_consecutive_chars > 0:
            pattern = rf"(.)\1{{{self.config.max_consecutive_chars},}}"
            if re.search(pattern, password):
                violations.append(
                    PolicyViolation(
                        PasswordPolicyViolation.CONSECUTIVE_CHARS,
                        f"Password cannot have more than {self.config.max_consecutive_chars} "
                        "consecutive identical characters",
                    )
                )

        # Banned pattern check
        password_lower = password.lower()
        for pattern in self.config.banned_patterns:
            if re.search(pattern, password_lower):
                violations.append(
                    PolicyViolation(
                        PasswordPolicyViolation.BANNED_PATTERN,
                        "Password contains a commonly used pattern",
                    )
                )
                break

        # Context-aware check (username, email in password)
        if self.config.block_context_words:
            for field in ["username", "email", "first_name", "last_name"]:
                context_value = user_context.get(field, "")
                if context_value and len(context_value) >= 3:
                    # For email, also check the local part
                    if field == "email" and "@" in context_value:
                        email_local = context_value.split("@")[0].lower()
                        if email_local in password_lower:
                            violations.append(
                                PolicyViolation(
                                    PasswordPolicyViolation.CONTEXT_WORD,
                                    f"Password cannot contain your {field}",
                                )
                            )
                            break
                    elif context_value.lower() in password_lower:
                        violations.append(
                            PolicyViolation(
                                PasswordPolicyViolation.CONTEXT_WORD,
                                f"Password cannot contain your {field}",
                            )
                        )
                        break

        # Breach check (async, can be slow)
        should_check_breach = (
            check_breach if check_breach is not None else self.config.check_breached
        )
        if should_check_breach and len(violations) == 0:
            # Only check breach if no other errors (to save API calls)
            is_breached, count = await check_password_breach(password)
            if is_breached:
                violations.append(
                    PolicyViolation(
                        PasswordPolicyViolation.BREACHED,
                        f"Password found in {count:,} data breaches. Please choose a different password.",
                        severity="error",
                    )
                )

        return violations

    def validate_sync(
        self,
        password: str,
        user_context: dict[str, Any] | None = None,
    ) -> list[PolicyViolation]:
        """
        Synchronous validation (without breach check).

        Use this in non-async contexts. Note: breach check is skipped.
        """
        import asyncio

        async def _validate():
            return await self.validate(password, user_context, check_breach=False)

        return asyncio.run(_validate())


# =============================================================================
# Default Policy Instance
# =============================================================================

default_policy = PasswordPolicy()


async def validate_password(
    password: str,
    user_context: dict[str, Any] | None = None,
) -> list[PolicyViolation]:
    """Convenience function using default policy."""
    return await default_policy.validate(password, user_context)


# =============================================================================
# Password Security Audit
# =============================================================================


@dataclass
class PasswordAuditResult:
    """Result of password security audit."""

    entropy_bits: float
    algorithm: str
    needs_upgrade: bool
    is_breached: bool
    breach_count: int

    @property
    def strength_level(self) -> str:
        if self.entropy_bits >= 80:
            return "very_strong"
        elif self.entropy_bits >= 60:
            return "strong"
        elif self.entropy_bits >= 40:
            return "moderate"
        else:
            return "weak"


async def audit_password(
    password: str,
    hashed_password: str | None = None,
) -> PasswordAuditResult:
    """
    Perform security audit on a password.

    Args:
        password: Plain text password
        hashed_password: Optional existing hash to check algorithm

    Returns:
        PasswordAuditResult with security metrics
    """
    entropy = calculate_entropy(password)
    algorithm = get_hash_algorithm(hashed_password) if hashed_password else "n/a"
    needs_upgrade = needs_rehash(hashed_password) if hashed_password else False
    is_breached, breach_count = await check_password_breach(password)

    return PasswordAuditResult(
        entropy_bits=entropy,
        algorithm=algorithm,
        needs_upgrade=needs_upgrade,
        is_breached=is_breached,
        breach_count=breach_count,
    )
