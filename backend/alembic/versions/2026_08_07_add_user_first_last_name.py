"""add user first_name and last_name fields

Revision ID: c8d9e0f1a2b3
Revises: b982c771a39f
Create Date: 2026-08-07 18:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b982c771a39f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add first_name and last_name columns to users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('first_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('last_name', sa.String(length=255), nullable=True))
        batch_op.alter_column('name', nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('last_name')
        batch_op.drop_column('first_name')
        batch_op.alter_column('name', nullable=False)
