"""Finalize JSON storage types for live metadata parity.

Revision ID: g0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-08-08
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g0b1c2d3e4f5"
down_revision: str | Sequence[str] | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert legacy JSON columns to JSONB where the conversion is pending."""
    op.execute(
        """
        DO $$
        DECLARE column_type text;
        BEGIN
            SELECT data_type
            INTO column_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'projects'
              AND column_name = 'settings';

            IF column_type = 'json' THEN
                ALTER TABLE projects ALTER COLUMN settings DROP DEFAULT;
                ALTER TABLE projects
                    ALTER COLUMN settings TYPE JSONB
                    USING settings::jsonb;
                ALTER TABLE projects ALTER COLUMN settings SET DEFAULT '{}'::jsonb;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE column_type text;
        BEGIN
            SELECT data_type
            INTO column_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'security_logs'
              AND column_name = 'details';

            IF column_type = 'json' THEN
                ALTER TABLE security_logs
                    ALTER COLUMN details TYPE JSONB
                    USING details::jsonb;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Revert JSONB columns to JSON representations."""
    op.execute("ALTER TABLE projects ALTER COLUMN settings DROP DEFAULT")
    op.execute("ALTER TABLE projects ALTER COLUMN settings TYPE JSON USING settings::json")
    op.execute("ALTER TABLE projects ALTER COLUMN settings SET DEFAULT '{}'")
    op.execute("ALTER TABLE security_logs ALTER COLUMN details TYPE JSON USING details::json")
