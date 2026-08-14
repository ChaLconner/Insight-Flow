"""Merge Alembic heads, add search indexes, and create the durable job queue.

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3, a1b2c3d4e5f6
Create Date: 2026-08-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

_NOW_SQL = "now()"

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = ("c8d9e0f1a2b3", "a1b2c3d4e5f6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Converge schema history and add operationally required structures."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text(_NOW_SQL), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text(_NOW_SQL), nullable=False
        ),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text(_NOW_SQL)
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=100), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_background_jobs_idempotency_key"),
    )
    op.create_index(
        "ix_background_jobs_status_available_at",
        "background_jobs",
        ["status", "available_at"],
        unique=False,
    )
    op.create_index(
        "ix_background_jobs_status_locked_at",
        "background_jobs",
        ["status", "locked_at"],
        unique=False,
    )
    op.create_index(
        "ix_background_jobs_available_at",
        "background_jobs",
        ["available_at"],
        unique=False,
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projects_name_trgm "
        "ON projects USING gin (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projects_description_trgm "
        "ON projects USING gin (description gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tasks_title_trgm "
        "ON tasks USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tasks_description_trgm "
        "ON tasks USING gin (description gin_trgm_ops)"
    )


def downgrade() -> None:
    """Remove structures introduced by this operational migration."""
    op.execute("DROP INDEX IF EXISTS ix_tasks_description_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tasks_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_projects_description_trgm")
    op.execute("DROP INDEX IF EXISTS ix_projects_name_trgm")
    op.drop_index("ix_background_jobs_available_at", table_name="background_jobs")
    op.drop_index("ix_background_jobs_status_locked_at", table_name="background_jobs")
    op.drop_index("ix_background_jobs_status_available_at", table_name="background_jobs")
    op.drop_table("background_jobs")
