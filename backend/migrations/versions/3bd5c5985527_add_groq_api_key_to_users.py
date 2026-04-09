"""add_groq_api_key_to_users

Revision ID: 3bd5c5985527
Revises: 002
Create Date: 2026-04-07 17:14:03.945259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bd5c5985527'
down_revision: Union[str, Sequence[str], None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('groq_api_key', sa.String(255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'groq_api_key')
