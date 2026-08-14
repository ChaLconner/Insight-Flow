from unittest.mock import Mock

from sqlalchemy import create_engine, inspect

from legacy_schema import MIGRATION_OWNED_TABLES, Base, bootstrap_legacy_schema


def test_bootstrap_legacy_schema_leaves_revision_owned_tables_for_alembic():
    engine = create_engine("sqlite:///:memory:")

    try:
        bootstrap_legacy_schema(engine)
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert tables.isdisjoint(MIGRATION_OWNED_TABLES)
    assert {"users", "projects", "tasks", "task_history"}.issubset(tables)


def test_bootstrap_legacy_schema_enables_postgres_trigram_extension(monkeypatch):
    connection = Mock()
    connection.dialect.name = "postgresql"
    create_all = Mock()
    monkeypatch.setattr(Base.metadata, "create_all", create_all)

    bootstrap_legacy_schema(connection)

    connection.exec_driver_sql.assert_called_once_with("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    create_all.assert_called_once()
