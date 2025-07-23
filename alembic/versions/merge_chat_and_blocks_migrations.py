"""merge chat and blocks migrations

Revision ID: merge_chat_and_blocks
Revises: 4867d799c984, 7fe74aee49e3
Create Date: 2025-01-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'merge_chat_and_blocks'
down_revision: Union[str, None] = ('4867d799c984', '7fe74aee49e3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is a merge migration - no changes needed
    pass


def downgrade() -> None:
    # This is a merge migration - no changes needed
    pass 