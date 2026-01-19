"""
Database configuration for Insight-Flow application.
Configured for comprehensive Async I/O using SQLAlchemy 2.0+ and asyncpg.
"""

import logging
import os
from collections.abc import AsyncGenerator, Callable

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import get_settings
from models import Base

# Load settings
settings = get_settings()

# Initialize Logger
db_logger = logging.getLogger("database")
db_logger.info("=" * 50)
db_logger.info("DATABASE CONFIGURATION (ASYNC)")

# Construct Async Database URL
database_url = settings.database.url

# Ensure correct driver for async (asyncpg)
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql+pg8000://"):
    database_url = database_url.replace("postgresql+pg8000://", "postgresql+asyncpg://", 1)

# Redact password from logged URL for security
redacted_url = database_url
if "@" in redacted_url and ":" in redacted_url:
    try:
        prefix = redacted_url.split("@")[0]
        suffix = redacted_url.split("@")[1]
        if ":" in prefix:
            user_part = prefix.split(":")[0]
            # Keep scheme and user, hide password
            scheme_part = user_part.split("://")[0] + "://"
            username = user_part.split("://")[1] if "://" in user_part else user_part
            redacted_url = f"{scheme_part}{username}:****@{suffix}"
    except Exception:
        redacted_url = "postgresql+asyncpg://****:****@****"

db_logger.info(f"DATABASE_URL: {redacted_url}")
db_logger.info("=" * 50)

# Async connection args - asyncpg uses 'ssl' parameter instead of 'sslmode'
# For Neon and other cloud PostgreSQL providers, we need SSL
# Disable SSL for localhost to avoid connection issues in local development
is_localhost = "localhost" in database_url or "127.0.0.1" in database_url
if "pg8000" in database_url or "?" in database_url:
    # Clean potential leftovers if manual edits happened, though replaced above
    database_url = database_url.split("?")[0]

async_connect_args = {
    "ssl": "require" if not is_localhost else None,
    "command_timeout": 30,  # Query timeout in seconds
}

# Create Async Engine
# Create Async Engine
if os.environ.get("TESTING") == "true":
    db_logger.info("TESTING MODE: Skipping Async Engine Creation")
    async_engine = None

    class DummyResult:
        def scalars(self):
            return self

        def scalar_one_or_none(self):
            return None

        def scalar(self):
            return None

        def first(self):
            return None

        def all(self):
            return []

        def one_or_none(self):
            return None

        def fetchone(self):
            return None

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def commit(self):
            pass

        async def rollback(self):
            pass

        async def close(self):
            pass

        async def execute(self, *_args, **_kwargs):
            return DummyResult()

        async def scalar(self, *_args, **_kwargs):
            return None

        async def scalars(self, *_args, **_kwargs):
            return DummyResult()

        def add(self, *_args, **_kwargs):
            pass

        async def refresh(self, *_args, **_kwargs):
            pass

        async def get(self, *_args, **_kwargs):
            return None

        async def delete(self, *_args, **_kwargs):
            pass

    AsyncSessionLocal: Callable[..., AsyncSession] = DummySession  # type: ignore
else:
    async_engine = create_async_engine(
        database_url,  # ... original args ...
        echo=settings.database.echo,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
        pool_recycle=settings.database.pool_recycle,
        pool_pre_ping=True,
        connect_args=async_connect_args,
    )

    # Create Async Session Factory
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


async def get_async_db() -> AsyncGenerator[AsyncSession]:
    """
    Dependency for getting async database session.
    Use this in FastAPI routers:
    async def get_items(db: AsyncSession = Depends(get_async_db)):
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except HTTPException:
        # Don't log HTTP exceptions as database errors, just rollback
        await session.rollback()
        raise
    except Exception as e:
        db_logger.error(f"Database session error: {e}")
        await session.rollback()
        raise e
    finally:
        await session.close()


async def init_database():
    """
    Initialize database.
    Useful for checking connection on startup.
    """
    try:
        if async_engine is None:
            raise RuntimeError("Database engine is not initialized")
        async with async_engine.begin() as conn:
            # Just a simple ping to ensure connection works
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_logger.error(f"Database connection check failed: {e}")
        raise e


# Helper to execute raw SQL (Async)
async def execute_sql(sql_statement: str):
    """
    Execute raw SQL statement asynchronously.
    """
    if async_engine is None:
        raise RuntimeError("Database engine is not initialized")
    async with async_engine.begin() as conn:
        result = await conn.execute(text(sql_statement))
        return result


def drop_tables():
    """
    Drop all database tables.
    DANGEROUS: For testing only.
    """
    import asyncio

    async def _drop():
        if async_engine is None:
            return
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(_drop())
