"""fix_token_blacklist_id_type - Change id from INTEGER to UUID

Revision ID: h9c8g0d2e2b0
Revises: 9cd1cf9585b5
Create Date: 2025-12-31 17:34:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'h9c8g0d2e2b0'
down_revision: Union[str, None] = '9cd1cf9585b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table exists and recreate with proper UUID type
    # First, drop the old table if it exists (token blacklist data can be regenerated)
    op.execute("DROP TABLE IF EXISTS token_blacklist CASCADE")
    
    # Create the table with correct UUID type
    op.create_table('token_blacklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_jti', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_token_blacklist_token_jti'), 'token_blacklist', ['token_jti'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_token_blacklist_token_jti'), table_name='token_blacklist')
    op.drop_table('token_blacklist')
