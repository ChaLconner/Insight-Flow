"""Add github_id to users

Revision ID: add_github_id_001
Revises: 58e012fdb79c
Create Date: 2025-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_github_id_001'
down_revision: Union[str, None] = '58e012fdb79c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add github_id column to users table
    op.add_column('users', sa.Column('github_id', sa.String(255), nullable=True))
    # Create unique index on github_id
    op.create_index('ix_users_github_id', 'users', ['github_id'], unique=True)


def downgrade() -> None:
    # Remove index and column
    op.drop_index('ix_users_github_id', table_name='users')
    op.drop_column('users', 'github_id')
