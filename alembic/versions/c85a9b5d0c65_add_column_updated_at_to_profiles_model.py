"""Add column updated_at to profiles model

Revision ID: c85a9b5d0c65
Revises: 3fa747b0968c
Create Date: 2025-03-09 17:38:56.775685

Legacy incremental migration superseded by 20260527_0001.
"""
from collections.abc import Sequence

revision: str = 'c85a9b5d0c65'
down_revision: str | None = '3fa747b0968c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
