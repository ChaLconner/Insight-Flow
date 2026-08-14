"""add_analytics_performance_indexes

Revision ID: a1b2c3d4e5f6
Revises: b5ef0dbf845a
Create Date: 2026-04-29 19:15:00.000000

Migration Description:
    Add composite indexes to accelerate analytics and dashboard queries.
    These indexes cover the most common filter/sort patterns in:
    - AsyncDashboardService (task_history by activity_type + timestamp)
    - AsyncAnalyticsService (task_history by user, projects by owner)
    - AsyncProjectService (tasks by assignee + status)
"""
import os
import sys
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# Add backend directory to path for migration_helpers import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from migration_helpers import safe_create_index, safe_drop_index

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = 'b5ef0dbf845a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite indexes for analytics and dashboard query performance."""
    # B4: task_history — covers dashboard velocity, analytics trends filtering
    safe_create_index(
        'ix_task_history_project_activity_timestamp',
        'task_history',
        ['project_id', 'activity_type', 'timestamp'],
    )
    # B4: task_history — covers per-user activity stats in dashboard
    safe_create_index(
        'ix_task_history_user_activity_timestamp',
        'task_history',
        ['user_id', 'activity_type', 'timestamp'],
    )
    # B4: tasks — covers dashboard pending review (assignee + status combo)
    safe_create_index(
        'ix_tasks_assignee_status',
        'tasks',
        ['assignee_id', 'status'],
    )
    # B4: projects — covers project listing sort/filter by owner
    safe_create_index(
        'ix_projects_owner_created_at',
        'projects',
        ['owner_id', 'created_at'],
    )
    # B4: projects — covers active project filtering
    safe_create_index(
        'ix_projects_owner_is_active',
        'projects',
        ['owner_id', 'is_active'],
    )


def downgrade() -> None:
    """Remove analytics performance indexes."""
    safe_drop_index('ix_projects_owner_is_active', 'projects')
    safe_drop_index('ix_projects_owner_created_at', 'projects')
    safe_drop_index('ix_tasks_assignee_status', 'tasks')
    safe_drop_index('ix_task_history_user_activity_timestamp', 'task_history')
    safe_drop_index('ix_task_history_project_activity_timestamp', 'task_history')
