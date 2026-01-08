"""
Initialize database for CI environment.
Creates all tables using SQLAlchemy metadata and stamps Alembic version.
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from models import Base


async def wait_for_db(engine, max_retries: int = 30, delay: float = 1.0) -> bool:
    """
    Wait for database to be ready for connections.

    Args:
        engine: SQLAlchemy async engine
        max_retries: Maximum number of connection attempts
        delay: Seconds to wait between retries

    Returns:
        True if connection successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                print(f"✓ Database connection successful on attempt {attempt}")
                return True
        except Exception as e:
            print(f"Attempt {attempt}/{max_retries}: Database not ready - {e}")
            if attempt < max_retries:
                await asyncio.sleep(delay)
    return False


async def init_database():
    """Create all tables and stamp alembic version."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    print("=" * 60)
    print("CI DATABASE INITIALIZATION")
    print("=" * 60)

    # Mask password in log output
    if "@" in database_url:
        parts = database_url.split("@")
        user_part = parts[0].rsplit(":", 1)[0]
        safe_url = f"{user_part}:****@{parts[1]}"
    else:
        safe_url = database_url
    print(f"DATABASE_URL: {safe_url}")

    engine = create_async_engine(database_url, echo=False)

    try:
        # Wait for database to be ready
        print("\n[1/4] Waiting for database connection...")
        if not await wait_for_db(engine):
            raise RuntimeError("Could not connect to database after maximum retries")

        async with engine.begin() as conn:
            # Create all tables
            print("\n[2/4] Creating tables from SQLAlchemy metadata...")
            await conn.run_sync(Base.metadata.create_all)
            print("✓ Tables created successfully")

            # Create alembic_version table and stamp to latest
            print("\n[3/4] Setting up Alembic version tracking...")
            await conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """)
            )

            # Stamp to the latest revision (v_token_expiry_001 is current head)
            await conn.execute(text("DELETE FROM alembic_version"))
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('v_token_expiry_001')")
            )
            print("✓ Alembic stamped to version: v_token_expiry_001 (head)")

            # Verify critical tables exist
            print("\n[4/4] Verifying table creation...")
            result = await conn.execute(
                text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            )
            tables = [row[0] for row in result.fetchall()]

            # Check for critical tables that caused errors in CI
            critical_tables = ["users", "auth_audits", "projects", "tasks"]
            missing_tables = [t for t in critical_tables if t not in tables]

            if missing_tables:
                raise RuntimeError(f"Missing critical tables: {missing_tables}")

            print(
                f"✓ Found {len(tables)} tables: {', '.join(tables[:10])}{'...' if len(tables) > 10 else ''}"
            )

        print("\n" + "=" * 60)
        print("✓ DATABASE INITIALIZATION COMPLETE")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ ERROR during database initialization: {e}")
        raise
    finally:
        # Ensure engine is properly disposed to avoid "Event loop is closed" errors
        await engine.dispose()
        print("✓ Engine disposed cleanly")


if __name__ == "__main__":
    asyncio.run(init_database())
