from sqlalchemy import create_engine, inspect

from legacy_schema import MIGRATION_OWNED_TABLES, bootstrap_legacy_schema


def test_bootstrap_legacy_schema_leaves_revision_owned_tables_for_alembic():
    engine = create_engine("sqlite:///:memory:")

    try:
        bootstrap_legacy_schema(engine)
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert tables.isdisjoint(MIGRATION_OWNED_TABLES)
    assert {"users", "projects", "tasks", "task_history"}.issubset(tables)
