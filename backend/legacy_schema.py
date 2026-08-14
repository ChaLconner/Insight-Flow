"""Compatibility bootstrap for the pre-Alembic model-owned schema."""

from sqlalchemy.engine import Connection

from models import Base

# These tables are created by explicit Alembic revisions later in the chain.
# Creating them from current metadata before those revisions would cause the
# historical create-table migrations to be skipped or fail.
MIGRATION_OWNED_TABLES = frozenset(
    {"payment_methods", "subscriptions", "payment_history", "background_jobs"}
)


def bootstrap_legacy_schema(connection: Connection) -> None:
    """Create the legacy model-owned tables required by the old chain."""
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    tables = [
        table for table in Base.metadata.sorted_tables if table.name not in MIGRATION_OWNED_TABLES
    ]
    Base.metadata.create_all(connection, tables=tables)
