"""
Application configuration management using Pydantic Settings.
Provides type-safe, validated configuration with environment variable support.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    url: str = Field(..., alias="DATABASE_URL")
    pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=300, alias="DB_POOL_RECYCLE")
    echo: bool = Field(default=False, alias="DB_ECHO")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


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
        default="http://localhost:3000/auth/callback",
        alias="GOOGLE_REDIRECT_URI"
    )
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class CORSSettings(BaseSettings):
    """CORS configuration settings."""
    origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS"
    )
    allow_credentials: bool = Field(default=True)
    allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    )
    allow_headers: List[str] = Field(default=["*"])
    
    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.origins.split(",")]
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class CacheSettings(BaseSettings):
    """Cache configuration settings."""
    enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    default_timeout: int = Field(default=60, alias="CACHE_DEFAULT_TIMEOUT")
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: str = Field(default="text", alias="LOG_FORMAT")  # text or json
    file_path: Optional[str] = Field(default=None, alias="LOG_FILE_PATH")
    
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
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class AppSettings(BaseSettings):
    """Main application settings."""
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    app_name: str = Field(default="Insight-Flow", alias="APP_NAME")
    api_version: str = Field(default="1.0.0", alias="API_VERSION")
    
    # Server settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # Trusted hosts
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1,0.0.0.0,testserver",
        alias="ALLOWED_HOSTS"
    )
    
    # Feature flags
    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    
    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        return [host.strip() for host in self.allowed_hosts.split(",")]
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
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
