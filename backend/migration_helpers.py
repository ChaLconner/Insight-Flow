"""
Alembic Migration Helper Utilities

This module provides safe migration operations that check for existing
database objects before attempting to create or drop them. This prevents
PostgreSQL transaction abort errors in async environments.

Usage in migration scripts:
    from alembic.migration_helpers import (
        safe_add_column, safe_drop_column,
        safe_create_index, safe_drop_index,
        safe_create_table, safe_drop_table
    )
"""

from typing import Any

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op


def get_inspector():
    """Get a SQLAlchemy inspector for the current connection."""
    conn = op.get_bind()
    return inspect(conn)


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = get_inspector()
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    inspector = get_inspector()
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = get_inspector()
    return table_name in inspector.get_table_names()


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a constraint exists on a table."""
    inspector = get_inspector()
    # Check unique constraints
    unique_constraints = inspector.get_unique_constraints(table_name)
    if constraint_name in [c["name"] for c in unique_constraints]:
        return True
    # Check foreign keys
    fks = inspector.get_foreign_keys(table_name)
    if constraint_name in [fk["name"] for fk in fks if fk["name"]]:
        return True
    # Check primary key
    pk = inspector.get_pk_constraint(table_name)
    return bool(pk and pk.get("name") == constraint_name)


def safe_add_column(table_name: str, column: sa.Column, **kwargs: Any) -> bool:
    """
    Safely add a column to a table if it doesn't already exist.

    Args:
        table_name: Name of the table to add the column to
        column: SQLAlchemy Column object to add
        **kwargs: Additional arguments to pass to op.add_column

    Returns:
        True if column was added, False if it already existed
    """
    if not column_exists(table_name, column.name):
        op.add_column(table_name, column, **kwargs)
        return True
    return False


def safe_drop_column(table_name: str, column_name: str, **kwargs: Any) -> bool:
    """
    Safely drop a column from a table if it exists.

    Args:
        table_name: Name of the table
        column_name: Name of the column to drop
        **kwargs: Additional arguments to pass to op.drop_column

    Returns:
        True if column was dropped, False if it didn't exist
    """
    if column_exists(table_name, column_name):
        op.drop_column(table_name, column_name, **kwargs)
        return True
    return False


def safe_create_index(
    index_name: str, table_name: str, columns: list[str], unique: bool = False, **kwargs: Any
) -> bool:
    """
    Safely create an index if it doesn't already exist.

    Args:
        index_name: Name of the index to create
        table_name: Name of the table
        columns: List of column names to include in the index
        unique: Whether the index should be unique
        **kwargs: Additional arguments to pass to op.create_index

    Returns:
        True if index was created, False if it already existed
    """
    if not index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique, **kwargs)
        return True
    return False


def safe_drop_index(index_name: str, table_name: str, **kwargs: Any) -> bool:
    """
    Safely drop an index if it exists.

    Args:
        index_name: Name of the index to drop
        table_name: Name of the table
        **kwargs: Additional arguments to pass to op.drop_index

    Returns:
        True if index was dropped, False if it didn't exist
    """
    if index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name, **kwargs)
        return True
    return False


def safe_create_table(table_name: str, *columns: sa.Column, **kwargs: Any) -> bool:
    """
    Safely create a table if it doesn't already exist.

    Args:
        table_name: Name of the table to create
        *columns: Column definitions
        **kwargs: Additional arguments to pass to op.create_table

    Returns:
        True if table was created, False if it already existed
    """
    if not table_exists(table_name):
        op.create_table(table_name, *columns, **kwargs)
        return True
    return False


def safe_drop_table(table_name: str, **kwargs: Any) -> bool:
    """
    Safely drop a table if it exists.

    Args:
        table_name: Name of the table to drop
        **kwargs: Additional arguments to pass to op.drop_table

    Returns:
        True if table was dropped, False if it didn't exist
    """
    if table_exists(table_name):
        op.drop_table(table_name, **kwargs)
        return True
    return False


def safe_create_foreign_key(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    **kwargs: Any,
) -> bool:
    """
    Safely create a foreign key constraint if it doesn't already exist.

    Args:
        constraint_name: Name of the constraint
        source_table: Source table name
        referent_table: Referenced table name
        local_cols: Local column names
        remote_cols: Remote column names
        **kwargs: Additional arguments

    Returns:
        True if constraint was created, False if it already existed
    """
    if not constraint_exists(source_table, constraint_name):
        op.create_foreign_key(
            constraint_name, source_table, referent_table, local_cols, remote_cols, **kwargs
        )
        return True
    return False


def safe_drop_constraint(
    constraint_name: str, table_name: str, type_: str | None = None, **kwargs: Any
) -> bool:
    """
    Safely drop a constraint if it exists.

    Args:
        constraint_name: Name of the constraint to drop
        table_name: Name of the table
        type_: Type of constraint (foreignkey, unique, etc.)
        **kwargs: Additional arguments

    Returns:
        True if constraint was dropped, False if it didn't exist
    """
    if constraint_exists(table_name, constraint_name):
        op.drop_constraint(constraint_name, table_name, type_=type_, **kwargs)
        return True
    return False


def safe_create_unique_constraint(
    constraint_name: str, table_name: str, columns: list[str], **kwargs: Any
) -> bool:
    """
    Safely create a unique constraint if it doesn't already exist.

    Args:
        constraint_name: Name of the constraint
        table_name: Name of the table
        columns: List of column names for the constraint
        **kwargs: Additional arguments

    Returns:
        True if constraint was created, False if it already existed
    """
    if not constraint_exists(table_name, constraint_name):
        op.create_unique_constraint(constraint_name, table_name, columns, **kwargs)
        return True
    return False
