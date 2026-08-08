"""Reconcile project contracts, integrity constraints, and operational indexes.

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-08-08
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_unique_constraint(table: str, name: str, columns: str) -> None:
    """Add a unique constraint while preserving safe upgrades from drifted schemas."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM {table}
                GROUP BY {columns}
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION 'Cannot add {name}: duplicate rows exist in {table}';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = '{name}'
                  AND conrelid = 'public.{table}'::regclass
            ) THEN
                ALTER TABLE {table}
                    ADD CONSTRAINT {name} UNIQUE ({columns});
            END IF;
        END $$;
        """
    )


def _add_check_constraint(table: str, name: str, expression: str) -> None:
    """Add a domain check once, allowing PostgreSQL to validate existing data."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = '{name}'
                  AND conrelid = 'public.{table}'::regclass
            ) THEN
                ALTER TABLE {table}
                    ADD CONSTRAINT {name} CHECK ({expression});
            END IF;
        END $$;
        """
    )


def _normalize_boolean_column(table: str, column: str, true_values: str) -> None:
    """Convert legacy text booleans without touching already-correct schemas."""
    escaped_values = true_values.replace("'", "''")
    op.execute(
        f"""
        DO $$
        DECLARE column_type text;
        BEGIN
            SELECT data_type
            INTO column_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = '{table}'
              AND column_name = '{column}';

            IF column_type IN ('character varying', 'text') THEN
                EXECUTE 'UPDATE {table} SET {column} = CASE
                    WHEN lower(trim({column})) IN ({escaped_values}) THEN ''true''
                    ELSE ''false''
                END';

                EXECUTE 'ALTER TABLE {table}
                    ALTER COLUMN {column} TYPE boolean
                    USING lower(trim({column})) IN ({escaped_values})';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    """Apply schema, linking, and query-path invariants."""
    # Persist fields already exposed by the frontend project contract.
    op.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS color VARCHAR(7)")
    op.execute("UPDATE projects SET color = '#6366f1' WHERE color IS NULL")
    op.execute("ALTER TABLE projects ALTER COLUMN color SET DEFAULT '#6366f1'")
    op.execute("ALTER TABLE projects ALTER COLUMN color SET NOT NULL")

    op.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS settings JSON")
    op.execute("UPDATE projects SET settings = '{}' WHERE settings IS NULL")
    op.execute("ALTER TABLE projects ALTER COLUMN settings SET DEFAULT '{}'")
    op.execute("ALTER TABLE projects ALTER COLUMN settings SET NOT NULL")

    # Normalize legacy string booleans before the model changes to Boolean.
    _normalize_boolean_column("task_time_tracking", "is_active", "'active', 'true', '1', 'yes'")
    _normalize_boolean_column("task_comments", "is_edited", "'true', '1', 'yes'")
    op.execute("ALTER TABLE task_time_tracking ALTER COLUMN is_active SET DEFAULT true")
    op.execute("ALTER TABLE task_time_tracking ALTER COLUMN is_active SET NOT NULL")
    op.execute("ALTER TABLE task_comments ALTER COLUMN is_edited SET DEFAULT false")
    op.execute("ALTER TABLE task_comments ALTER COLUMN is_edited SET NOT NULL")

    # Every project owner must also be represented in the membership graph so
    # member counts, member responses, and assignment checks use one invariant.
    # Existing owner rows are normalized without creating duplicates.
    op.execute(
        """
        UPDATE project_members pm
        SET role = 'owner'
        FROM projects p
        WHERE pm.project_id = p.id
          AND pm.user_id = p.owner_id
        """
    )
    op.execute(
        """
        INSERT INTO project_members (id, project_id, user_id, role)
        SELECT gen_random_uuid(), p.id, p.owner_id, 'owner'
        FROM projects p
        WHERE NOT EXISTS (
            SELECT 1
            FROM project_members pm
            WHERE pm.project_id = p.id
            AND pm.user_id = p.owner_id
        )
        ON CONFLICT (project_id, user_id) DO NOTHING
        """
    )

    # Domain constraints prevent future invalid links and duplicate facts.
    _add_unique_constraint(
        "project_analytics",
        "uq_project_analytics_project_period_date",
        "project_id, period, date",
    )
    _add_unique_constraint(
        "user_productivity",
        "uq_user_productivity_user_project_period_date",
        "user_id, project_id, period, date",
    )
    _add_unique_constraint(
        "task_dependencies",
        "uq_task_dependencies_pair_type",
        "task_id, depends_on_task_id, dependency_type",
    )
    _add_unique_constraint(
        "project_tag_associations",
        "uq_project_tag_associations_pair",
        "project_id, tag_id",
    )
    _add_check_constraint(
        "task_dependencies",
        "ck_task_dependencies_not_self",
        "task_id <> depends_on_task_id",
    )
    _add_check_constraint(
        "project_milestones",
        "ck_project_milestones_status",
        "is_completed IN ('pending', 'completed', 'cancelled')",
    )
    _add_check_constraint(
        "project_milestones",
        "ck_project_milestones_progress",
        "progress_percentage BETWEEN 0 AND 100",
    )

    # Foreign-key lookup and cleanup indexes.
    op.execute("CREATE INDEX IF NOT EXISTS ix_auth_audits_user_id ON auth_audits (user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_payment_history_subscription_id "
        "ON payment_history (subscription_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_payment_history_payment_method_id "
        "ON payment_history (payment_method_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subscriptions_default_payment_method_id "
        "ON subscriptions (default_payment_method_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_token_blacklist_expires_at ON token_blacklist (expires_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_task_comments_task_created_at "
        "ON task_comments (task_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_project_members_project_created_at "
        "ON project_members (project_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_type_created_at "
        "ON notifications (user_id, type, created_at)"
    )

    # Unique constraints already provide equivalent left-prefix coverage.
    op.execute("DROP INDEX IF EXISTS ix_project_members_project_user")
    op.execute("DROP INDEX IF EXISTS ix_user_favorites_user_project")


def downgrade() -> None:
    """Reverse this migration; do not run in production without a rollback plan."""
    op.execute(
        "ALTER TABLE project_milestones DROP CONSTRAINT IF EXISTS ck_project_milestones_progress"
    )
    op.execute(
        "ALTER TABLE project_milestones DROP CONSTRAINT IF EXISTS ck_project_milestones_status"
    )
    op.execute(
        "ALTER TABLE task_dependencies DROP CONSTRAINT IF EXISTS ck_task_dependencies_not_self"
    )
    op.execute(
        "ALTER TABLE project_tag_associations DROP CONSTRAINT IF EXISTS uq_project_tag_associations_pair"
    )
    op.execute(
        "ALTER TABLE task_dependencies DROP CONSTRAINT IF EXISTS uq_task_dependencies_pair_type"
    )
    op.execute(
        "ALTER TABLE user_productivity "
        "DROP CONSTRAINT IF EXISTS uq_user_productivity_user_project_period_date"
    )
    op.execute(
        "ALTER TABLE project_analytics "
        "DROP CONSTRAINT IF EXISTS uq_project_analytics_project_period_date"
    )
    op.execute("DROP INDEX IF EXISTS ix_token_blacklist_expires_at")
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_default_payment_method_id")
    op.execute("DROP INDEX IF EXISTS ix_payment_history_payment_method_id")
    op.execute("DROP INDEX IF EXISTS ix_payment_history_subscription_id")
    op.execute("DROP INDEX IF EXISTS ix_auth_audits_user_id")
    op.execute("DROP INDEX IF EXISTS ix_task_comments_task_created_at")
    op.execute("DROP INDEX IF EXISTS ix_project_members_project_created_at")
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_type_created_at")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS settings")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS color")
