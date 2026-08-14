"""add_task_sorting_indexes

Revision ID: 9cd1cf9585b5
Revises: add_user_favorites_001
Create Date: 2025-12-29 23:51:16.945991

Migration Description:
    Add composite indexes for efficient task sorting and filtering.
    Also adds payment history index for user payment queries.

"""
import os
import sys
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Add backend directory to path for migration_helpers import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from migration_helpers import safe_create_index, safe_drop_index

# revision identifiers, used by Alembic.
revision: str = '9cd1cf9585b5'
down_revision: str | Sequence[str] | None = 'add_user_favorites_001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite indexes for efficient task sorting and queries."""
    # Create task sorting indexes (safe - won't fail if already exists)
    safe_create_index('ix_tasks_assignee_updated_at', 'tasks', ['assignee_id', 'updated_at'])
    safe_create_index('ix_tasks_project_updated_at', 'tasks', ['project_id', 'updated_at'])
    # Also adding payment history index here for user payment queries
    safe_create_index('ix_payment_history_user_created_at', 'payment_history', ['user_id', 'created_at'])


def downgrade() -> None:
    """Remove task sorting and payment history indexes."""
    safe_drop_index('ix_payment_history_user_created_at', 'payment_history')
    safe_drop_index('ix_tasks_project_updated_at', 'tasks')
    safe_drop_index('ix_tasks_assignee_updated_at', 'tasks')
