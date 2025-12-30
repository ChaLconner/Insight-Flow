"""add user_favorites table

Revision ID: add_user_favorites_001
Revises: g8b7f9c2d1a9
Create Date: 2025-12-28 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_favorites_001'
down_revision = 'g8b7f9c2d1a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_favorites table
    op.create_table(
        'user_favorites',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'project_id', name='uq_user_favorites_user_project')
    )
    
    # Create indexes
    op.create_index('ix_user_favorites_user_id', 'user_favorites', ['user_id'])
    op.create_index('ix_user_favorites_project_id', 'user_favorites', ['project_id'])
    op.create_index('ix_user_favorites_user_project', 'user_favorites', ['user_id', 'project_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_user_favorites_user_project', table_name='user_favorites')
    op.drop_index('ix_user_favorites_project_id', table_name='user_favorites')
    op.drop_index('ix_user_favorites_user_id', table_name='user_favorites')
    
    # Drop table
    op.drop_table('user_favorites')
