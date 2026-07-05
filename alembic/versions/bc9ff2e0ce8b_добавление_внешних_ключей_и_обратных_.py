"""Добавление внешних ключей и обратных отношений к User

Revision ID: bc9ff2e0ce8b
Revises: ffc086ad1de9
Create Date: 2025-03-11 16:13:54.429051

Legacy incremental migration superseded by 20260527_0001.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'bc9ff2e0ce8b'
down_revision: Union[str, None] = 'ffc086ad1de9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
