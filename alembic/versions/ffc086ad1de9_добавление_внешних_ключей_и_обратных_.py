"""Добавление внешних ключей и обратных отношений

Revision ID: ffc086ad1de9
Revises: c85a9b5d0c65
Create Date: 2025-03-11 15:25:20.308904

Legacy incremental migration superseded by 20260527_0001.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'ffc086ad1de9'
down_revision: Union[str, None] = 'c85a9b5d0c65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
