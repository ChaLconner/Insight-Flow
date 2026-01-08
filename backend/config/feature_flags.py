"""
Feature Flags System - Staff/Principal Level Configuration

Provides:
- Dynamic feature flag management
- Environment-aware defaults
- A/B testing support with percentage rollouts
- Thread-safe flag evaluation
- Context-aware flag overrides
"""

import contextvars
import hashlib
import os
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any

from utils.logger import setup_logger

logger = setup_logger("feature_flags")


# =============================================================================
# Feature Flag Core Types
# =============================================================================


class FlagType(Enum):
    """Type of feature flag."""

    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    STRING = "string"
    JSON = "json"


@dataclass
class FeatureFlag:
    """Definition of a feature flag."""

    name: str
    flag_type: FlagType
    default_value: Any
    description: str = ""

    # Environment-specific overrides
    production_value: Any = None
    staging_value: Any = None
    development_value: Any = None

    # Percentage rollout (0-100)
    rollout_percentage: int = 100

    # User segments for targeting
    enabled_for_users: set[str] = field(default_factory=set)
    disabled_for_users: set[str] = field(default_factory=set)

    def get_value_for_environment(self, environment: str) -> Any:
        """Get the appropriate value for the given environment."""
        if environment == "production" and self.production_value is not None:
            return self.production_value
        elif environment == "staging" and self.staging_value is not None:
            return self.staging_value
        elif environment == "development" and self.development_value is not None:
            return self.development_value
        return self.default_value


# =============================================================================
# Feature Flag Registry
# =============================================================================


class FeatureFlagRegistry:
    """
    Central registry for feature flags with thread-safe operations.

    Usage:
        flags = FeatureFlagRegistry()

        # Register flags
        flags.register(FeatureFlag(
            name="new_dashboard",
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            production_value=False,
            staging_value=True,
            description="Enable new dashboard UI"
        ))

        # Check flags
        if flags.is_enabled("new_dashboard"):
            render_new_dashboard()

        # Check with user context (for A/B testing)
        if flags.is_enabled_for_user("new_dashboard", user_id):
            render_new_dashboard()
    """

    def __init__(self):
        self._flags: dict[str, FeatureFlag] = {}
        self._lock = Lock()
        self._environment = os.getenv("ENVIRONMENT", "development")

        # Context for request-scoped overrides
        self._override_context: contextvars.ContextVar[dict[str, Any] | None] = (
            contextvars.ContextVar("flag_overrides", default=None)
        )

    def register(self, flag: FeatureFlag) -> None:
        """Register a feature flag."""
        with self._lock:
            self._flags[flag.name] = flag
            logger.debug(f"Registered feature flag: {flag.name}")

    def register_many(self, flags: list[FeatureFlag]) -> None:
        """Register multiple feature flags."""
        for flag in flags:
            self.register(flag)

    def get(self, name: str) -> Any:
        """Get the value of a feature flag."""
        # Check for request-scoped override first
        overrides = self._override_context.get()
        if overrides and name in overrides:
            return overrides[name]

        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                logger.warning(f"Unknown feature flag: {name}")
                return None
            return flag.get_value_for_environment(self._environment)

    def is_enabled(self, name: str) -> bool:
        """Check if a boolean feature flag is enabled."""
        value = self.get(name)
        return bool(value)

    def is_enabled_for_user(self, name: str, user_id: str) -> bool:
        """
        Check if a feature flag is enabled for a specific user.

        Supports:
        - Explicit user targeting (enabled_for_users, disabled_for_users)
        - Percentage rollout (consistent per user using hash)
        """
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                return False

            # Check explicit targeting
            if user_id in flag.disabled_for_users:
                return False
            if user_id in flag.enabled_for_users:
                return True

            # Check percentage rollout
            if flag.rollout_percentage < 100:
                # Use consistent hashing so same user always gets same result
                hash_input = f"{name}:{user_id}"
                hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
                bucket = hash_value % 100
                if bucket >= flag.rollout_percentage:
                    return False

            return bool(flag.get_value_for_environment(self._environment))

    @contextmanager
    def override(self, **overrides):
        """
        Temporarily override feature flags for the current context.

        Usage:
            with flags.override(new_dashboard=True):
                # Code here sees new_dashboard as True
                pass
        """
        ctx = self._override_context.get()
        current = ctx.copy() if ctx else {}
        token = self._override_context.set({**current, **overrides})
        try:
            yield
        finally:
            self._override_context.reset(token)

    def list_flags(self) -> dict[str, dict]:
        """List all registered flags with their current values."""
        with self._lock:
            return {
                name: {
                    "type": flag.flag_type.value,
                    "value": flag.get_value_for_environment(self._environment),
                    "description": flag.description,
                    "rollout_percentage": flag.rollout_percentage,
                }
                for name, flag in self._flags.items()
            }

    def update_flag(self, name: str, **updates) -> bool:
        """
        Dynamically update a flag's value.

        This allows runtime configuration changes without restart.
        """
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                return False

            for key, value in updates.items():
                if hasattr(flag, key):
                    setattr(flag, key, value)

            logger.info(f"Updated feature flag '{name}': {updates}")
            return True


# =============================================================================
# Global Feature Flag Instance
# =============================================================================

_feature_flags: FeatureFlagRegistry | None = None


def get_feature_flags() -> FeatureFlagRegistry:
    """Get the global feature flag registry."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlagRegistry()
        _register_default_flags(_feature_flags)
    return _feature_flags


def _register_default_flags(registry: FeatureFlagRegistry) -> None:
    """Register default feature flags from environment or config."""

    # Define default flags
    default_flags = [
        FeatureFlag(
            name="experimental_api",
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            development_value=True,
            description="Enable experimental API endpoints",
        ),
        FeatureFlag(
            name="rate_limiting_v2",
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            staging_value=True,
            description="Use new rate limiting algorithm",
        ),
        FeatureFlag(
            name="enhanced_analytics",
            flag_type=FlagType.BOOLEAN,
            default_value=True,
            description="Enable enhanced analytics tracking",
        ),
        FeatureFlag(
            name="ai_suggestions",
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            rollout_percentage=10,
            description="AI-powered task suggestions (10% rollout)",
        ),
        FeatureFlag(
            name="breach_check_on_login",
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            production_value=True,
            description="Check password breaches on login",
        ),
        FeatureFlag(
            name="distributed_tracing",
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            production_value=True,
            staging_value=True,
            description="Enable OpenTelemetry distributed tracing",
        ),
        FeatureFlag(
            name="max_concurrent_jobs",
            flag_type=FlagType.STRING,
            default_value="10",
            production_value="50",
            description="Maximum concurrent background jobs",
        ),
    ]

    registry.register_many(default_flags)

    # Load environment override flags (FF_* prefix)
    for key, value in os.environ.items():
        if key.startswith("FF_"):
            flag_name = key[3:].lower()  # FF_NEW_FEATURE -> new_feature
            registry.register(
                FeatureFlag(
                    name=flag_name,
                    flag_type=FlagType.BOOLEAN
                    if value.lower() in ("true", "false", "1", "0")
                    else FlagType.STRING,
                    default_value=value.lower() in ("true", "1")
                    if value.lower() in ("true", "false", "1", "0")
                    else value,
                    description=f"Environment override: {key}",
                )
            )


# =============================================================================
# Convenience Functions
# =============================================================================


def is_feature_enabled(name: str) -> bool:
    """Check if a feature is enabled."""
    return get_feature_flags().is_enabled(name)


def is_feature_enabled_for_user(name: str, user_id: str) -> bool:
    """Check if a feature is enabled for a specific user."""
    return get_feature_flags().is_enabled_for_user(name, user_id)


def get_feature_value(name: str) -> Any:
    """Get the value of a feature flag."""
    return get_feature_flags().get(name)


def feature_flag_decorator(flag_name: str, fallback: Callable | None = None):
    """
    Decorator to conditionally execute function based on feature flag.

    Usage:
        @feature_flag_decorator("new_algorithm")
        def new_algorithm():
            return "new"

        @feature_flag_decorator("new_algorithm", fallback=old_algorithm)
        def new_algorithm():
            return "new"
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if is_feature_enabled(flag_name):
                return func(*args, **kwargs)
            elif fallback:
                return fallback(*args, **kwargs)
            else:
                return None

        return wrapper

    return decorator
