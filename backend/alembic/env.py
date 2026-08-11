"""
Alembic Environment Configuration

This module configures Alembic for async database migrations with PostgreSQL.
It handles:
- Dynamic database URL configuration from environment variables
- Async engine setup using asyncpg driver
- Proper logging and error handling
- Both online and offline migration modes

Usage:
    alembic upgrade head     # Apply all migrations
    alembic downgrade -1     # Rollback one migration
    alembic revision --autogenerate -m "description"  # Create new migration
"""

import asyncio
import logging
import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import inspect, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

ASYNC_DATABASE_SCHEME = "postgresql+asyncpg://"

# Add the project root directory to the python path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

# Import Base from models for autogenerate support
from legacy_schema import bootstrap_legacy_schema
from models import Base

# Setup logging
logger = logging.getLogger("alembic.env")

# Target metadata for autogenerate support
target_metadata = Base.metadata


def compare_server_default(
    _context,
    inspected_column,
    metadata_column,
    _inspected_default,
    _metadata_default,
    _rendered_metadata_default,
):
    """Avoid PostgreSQL's unsupported equality comparison for JSON defaults."""
    if metadata_column.table.name == "projects" and metadata_column.name == "settings":
        return False
    if metadata_column.table.name == "security_logs" and metadata_column.name in {
        "id",
        "severity",
    }:
        return False
    return None


# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> str:
    """
    Get the database URL from environment variables.

    Automatically converts standard PostgreSQL URLs to use the asyncpg driver.

    Returns:
        str: The database URL configured for asyncpg, or empty string if not set.

    Raises:
        ValueError: If DATABASE_URL is not set in production environment.
    """
    url = os.getenv("DATABASE_URL", "")

    if not url:
        # Only warn in development, fail in production
        if os.getenv("ENVIRONMENT", "development") == "production":
            raise ValueError("DATABASE_URL environment variable is required in production")
        logger.warning("DATABASE_URL not set, migrations may fail")
        return ""

    original_url = url

    # Ensure usage of asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", ASYNC_DATABASE_SCHEME, 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", ASYNC_DATABASE_SCHEME, 1)
    elif url.startswith("postgresql+pg8000://"):
        url = url.replace("postgresql+pg8000://", ASYNC_DATABASE_SCHEME, 1)

    # Remove query parameters that may cause issues with asyncpg
    # (sslmode, etc. are handled differently by asyncpg)
    if "?" in url:
        base_url = url.split("?")[0]
        logger.debug("Removed query parameters from URL for asyncpg compatibility")
        url = base_url

    if url != original_url:
        logger.debug("Database URL converted to asyncpg driver")

    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the
    Engine creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output. This is useful for generating SQL scripts.

    Usage:
        alembic upgrade head --sql > migration.sql
    """
    url = get_url()

    logger.info("Running migrations in offline mode")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=compare_server_default,
    )

    with context.begin_transaction():
        context.run_migrations()

    logger.info("Offline migrations completed")


def do_run_migrations(connection: Connection) -> None:
    """
    Execute migrations using the provided database connection.

    Args:
        connection: SQLAlchemy Connection object
    """
    # The repository predates Alembic and has no historical baseline revision.
    # Bootstrap the model-owned legacy tables before replaying the chain so a
    # plain `alembic upgrade head` works on a new database as well as on an
    # existing legacy database. The four revision-owned tables remain for
    # their historical create-table migrations.
    if "alembic_version" not in inspect(connection).get_table_names():
        bootstrap_legacy_schema(connection)

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Detect column type changes
        compare_server_default=compare_server_default,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in async mode using asyncpg.

    This creates an async engine, establishes a connection,
    and runs migrations within a transaction.

    Raises:
        Exception: If migration fails, the error is logged and re-raised.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    logger.info("Starting async migrations...")

    # Use async engine with NullPool to avoid connection pooling issues
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.begin() as connection:
            await connection.run_sync(do_run_migrations)
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        raise
    finally:
        await connectable.dispose()
        logger.debug("Database connection disposed")


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    This is the standard mode for running migrations against a live database.
    Uses asyncio.run() to execute async migrations.
    """
    logger.info("Running migrations in online mode")
    asyncio.run(run_async_migrations())


# Entry point - determine which mode to run in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
