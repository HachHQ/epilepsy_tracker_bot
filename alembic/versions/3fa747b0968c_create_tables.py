"""Create tables

Revision ID: 3fa747b0968c
Revises: 4efdcf113b6d
Create Date: 2025-03-08 20:27:57.063784

Legacy incremental migration superseded by 20260527_0001.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '3fa747b0968c'
down_revision: Union[str, None] = '4efdcf113b6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
