"""Initialize CI or first-run deployment databases through Alembic."""

import asyncio
import os
import subprocess
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from legacy_schema import bootstrap_legacy_schema


async def ensure_legacy_schema(engine) -> None:
    """Create the pre-Alembic model schema required by the legacy chain."""
    async with engine.begin() as conn:
        await conn.run_sync(bootstrap_legacy_schema)


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


async def init_database():  # noqa: PLR0915
    """Wait for Postgres, apply migrations, and verify critical tables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    if os.getenv("LEGACY_SCHEMA_BOOTSTRAP", "false").lower() != "true":
        raise RuntimeError(
            "This compatibility bootstrap is intentionally explicit. "
            "Set LEGACY_SCHEMA_BOOTSTRAP=true only for the pre-Alembic schema path."
        )

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

        print("\n[2/5] Preparing explicitly requested legacy model schema...")
        await ensure_legacy_schema(engine)
        print("✓ Legacy model schema prepared")

        print("\n[3/5] Applying Alembic migrations...")
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migration_command = [sys.executable, "-m", "alembic", "upgrade", "head"]
        migration_process = await asyncio.create_subprocess_exec(
            *migration_command,
            cwd=backend_dir,
            env=os.environ.copy(),
        )
        migration_return_code = await migration_process.wait()
        if migration_return_code != 0:
            raise subprocess.CalledProcessError(migration_return_code, migration_command)
        print("✓ Alembic migrations applied successfully")

        async with engine.begin() as conn:
            # Verify critical tables
            print("\n[4/5] Verifying migrated tables...")
            result = await conn.execute(
                text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            )
            tables = [row[0] for row in result.fetchall()]

            # Check for critical tables that caused errors in CI
            critical_tables = ["users", "auth_audits", "projects", "tasks", "background_jobs"]
            missing_tables = [t for t in critical_tables if t not in tables]

            if missing_tables:
                raise RuntimeError(f"Missing critical tables: {missing_tables}")

            print(
                f"✓ Found {len(tables)} tables: {', '.join(tables[:10])}{'...' if len(tables) > 10 else ''}"
            )

            required_indexes = [
                "ix_tasks_project_status_priority",
                "ix_task_history_task_id_created_at",
                "ix_task_history_project_activity_timestamp",
                "ix_task_history_user_activity_timestamp",
                "ix_tasks_assignee_status",
                "ix_projects_owner_created_at",
                "ix_projects_owner_is_active",
                "ix_token_blacklist_expires_at",
                "ix_projects_name_trgm",
                "ix_tasks_title_trgm",
            ]
            index_result = await conn.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    """
                ),
            )
            found_indexes = {row[0] for row in index_result.fetchall()}
            missing_indexes = sorted(set(required_indexes) - found_indexes)
            if missing_indexes:
                raise RuntimeError(f"Missing required indexes: {missing_indexes}")
            print(f"✓ Verified required indexes: {', '.join(required_indexes)}")

            column_result = await conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'projects'
                    """
                ),
            )
            found_columns = {row[0] for row in column_result.fetchall()}
            required_project_columns = {"color", "settings"}
            missing_project_columns = sorted(required_project_columns - found_columns)
            if missing_project_columns:
                raise RuntimeError(
                    f"Project contract columns are incomplete: {missing_project_columns}"
                )
            print("✓ Verified project contract columns: color, settings")

            print("\n[5/5] Verifying Alembic version...")
            version_result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            versions = [row[0] for row in version_result.fetchall()]
            if len(versions) != 1:
                raise RuntimeError(f"Expected one Alembic head, found: {versions}")
            print(f"✓ Database is at Alembic head: {versions[0]}")

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
