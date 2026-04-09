"""add api_key to users

Revision ID: 004
Revises: 3bd5c5985527
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, Sequence[str], None] = '3bd5c5985527'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add api_key column to users table."""
    op.add_column('users', sa.Column('api_key', sa.String(64), nullable=True))
    op.create_index('idx_users_api_key', 'users', ['api_key'], unique=True)


def downgrade() -> None:
    """Remove api_key column from users table."""
    op.drop_index('idx_users_api_key', table_name='users')
    op.drop_column('users', 'api_key')
