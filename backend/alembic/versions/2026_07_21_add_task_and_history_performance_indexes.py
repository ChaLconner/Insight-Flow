"""add task and history performance indexes

Revision ID: b982c771a39f
Revises: 1fd46ce005d8
Create Date: 2026-07-21 15:40:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b982c771a39f'
down_revision: str | Sequence[str] | None = '1fd46ce005d8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create compound index for task status/priority queries per project
    op.create_index(
        'ix_tasks_project_status_priority',
        'tasks',
        ['project_id', 'status', 'priority'],
        unique=False,
        if_not_exists=True,
    )
    # Create index for task history queries by task and creation date
    op.create_index(
        'ix_task_history_task_id_created_at',
        'task_history',
        ['task_id', 'created_at'],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index('ix_task_history_task_id_created_at', table_name='task_history', if_exists=True)
    op.drop_index('ix_tasks_project_status_priority', table_name='tasks', if_exists=True)
