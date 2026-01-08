"""
Application configuration management using Pydantic Settings.
Provides type-safe, validated configuration with environment variable support.
"""

import os
from typing import Any
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, FieldValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    url: str = Field(..., alias="DATABASE_URL")
    pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=300, alias="DB_POOL_RECYCLE")
    echo: bool = Field(default=False, alias="DB_ECHO")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AuthSettings(BaseSettings):
    """Authentication configuration settings."""

    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Google OAuth
    google_client_id: str = Field(..., alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:3000/auth/callback", alias="GOOGLE_REDIRECT_URI"
    )

    # GitHub OAuth
    github_client_id: str | None = Field(default=None, alias="GITHUB_CLIENT_ID")
    github_client_secret: str | None = Field(default=None, alias="GITHUB_CLIENT_SECRET")
    github_redirect_uri: str = Field(
        default="http://localhost:3000/auth/callback/github", alias="GITHUB_REDIRECT_URI"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        # Forbidden default/weak values that should never be used
        forbidden_values = [
            "your_jwt_secret_key_here",
            "test_secret_key_placeholder",
            "dev",
            "secret",
            "development",
            "changeme",
            "your-secret-key",
            "supersecret",
            "mysecretkey",
        ]

        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")

        # Check against forbidden values (case-insensitive)
        if v.lower() in [f.lower() for f in forbidden_values]:
            raise ValueError(
                "SECRET_KEY must be changed from default value. "
                'Generate a secure key using: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

        # Check for simple patterns that might indicate a weak key
        if v == v[0] * len(v):  # All same character
            raise ValueError("SECRET_KEY cannot be a repeated single character")

        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class CORSSettings(BaseSettings):
    """
    CORS configuration settings with strict origin validation.

    Security Notes:
    - Wildcard '*' is NOT allowed for credentialed requests
    - All origins must be explicitly listed
    - Origins are validated for proper URL format
    - Trailing slashes are removed for consistency
    """

    origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ORIGINS"
    )
    allow_credentials: bool = Field(default=True)
    allow_methods: list[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
    allow_headers: list[str] = Field(default=["*"])

    @field_validator("origins")
    @classmethod
    def validate_origins(cls, v: str) -> str:
        """
        Validate that origins string doesn't contain wildcard when credentials are enabled.
        """
        if "*" in v:
            raise ValueError(
                "Wildcard '*' is not allowed in CORS_ORIGINS. "
                "Please specify explicit origins. "
                "Example: CORS_ORIGINS=http://localhost:3000,https://example.com"
            )
        return v

    @property
    def origins_list(self) -> list[str]:
        """
        Parse and validate CORS origins with strict security checks.

        Returns:
            List of validated origin URLs

        Raises:
            ValueError: If any origin is invalid
        """
        origins = []
        for origin in self.origins.split(","):
            # Strip whitespace
            cleaned = origin.strip()

            # Skip empty strings
            if not cleaned:
                continue

            # Remove trailing slash (CORS origins should not have trailing slashes)
            cleaned = cleaned.rstrip("/")

            # Validate URL format
            try:
                parsed = urlparse(cleaned)

                # Must have scheme and netloc
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError(
                        f"Invalid origin: '{origin}'. Must include scheme (http:// or https://)"
                    )

                # Only allow http and https schemes
                if parsed.scheme not in ("http", "https"):
                    raise ValueError(
                        f"Invalid scheme in origin: '{origin}'. Only http:// and https:// are allowed"
                    )

                # Reject wildcard
                if cleaned == "*":
                    raise ValueError(
                        "Wildcard '*' is not allowed. Please specify explicit origins."
                    )

                origins.append(cleaned)

            except ValueError as e:
                raise ValueError(f"Invalid CORS origin '{origin}': {e}")

        # Return at least localhost if nothing valid found
        if not origins:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]

        return origins

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class CacheSettings(BaseSettings):
    """Cache configuration settings."""

    enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    default_timeout: int = Field(default=60, alias="CACHE_DEFAULT_TIMEOUT")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: str = Field(default="text", alias="LOG_FORMAT")  # text or json
    file_path: str | None = Field(default=None, alias="LOG_FILE_PATH")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v.lower() not in ["text", "json"]:
            raise ValueError("LOG_FORMAT must be 'text' or 'json'")
        return v.lower()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class StripeSettings(BaseSettings):
    """Stripe payment gateway configuration settings."""

    secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    publishable_key: str | None = Field(default=None, alias="STRIPE_PUBLISHABLE_KEY")
    webhook_secret: str | None = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(self.secret_key and self.publishable_key)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppSettings(BaseSettings):
    """Main application settings."""

    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    app_name: str = Field(default="Insight-Flow", alias="APP_NAME")

    @field_validator("debug")
    @classmethod
    def validate_debug(cls, v: bool, info: Any) -> bool:
        """Security: Prevent DEBUG=True in production environment."""
        if v:
            # Check if environment is production
            env_value = info.data.get("environment") if info.data else None
            if env_value and env_value.lower() == "production":
                raise ValueError(
                    "DEBUG cannot be True in production environment. "
                    "Set ENVIRONMENT=development or remove DEBUG flag."
                )
        return v

    api_version: str = Field(default="1.0.0", alias="API_VERSION")

    # Server settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Trusted hosts
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1,0.0.0.0,testserver", alias="ALLOWED_HOSTS"
    )

    # Feature flags
    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")

    # Nested settings
    database: DatabaseSettings = Field(default_factory=lambda: DatabaseSettings())
    auth: AuthSettings = Field(default_factory=lambda: AuthSettings())
    cors: CORSSettings = Field(default_factory=lambda: CORSSettings())
    cache: CacheSettings = Field(default_factory=lambda: CacheSettings())
    logging: LoggingSettings = Field(default_factory=lambda: LoggingSettings())
    stripe: StripeSettings = Field(default_factory=lambda: StripeSettings())
    security_report_uri: str | None = Field(default=None, alias="SECURITY_REPORT_URI")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def is_testing(self) -> bool:
        return (
            self.environment.lower() == "testing" or os.getenv("TESTING", "false").lower() == "true"
        )

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",")]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> AppSettings:
    """
    Get cached application settings.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return AppSettings()


# Convenience functions for common settings access
def get_database_url() -> str:
    """Get database URL from settings."""
    return get_settings().database.url


def get_secret_key() -> str:
    """Get secret key from settings."""
    return get_settings().auth.secret_key


def is_production() -> bool:
    """Check if running in production environment."""
    return get_settings().is_production
