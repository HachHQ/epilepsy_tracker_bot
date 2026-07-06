"""Добавление внешних ключей и обратных отношений

Revision ID: ffc086ad1de9
Revises: c85a9b5d0c65
Create Date: 2025-03-11 15:25:20.308904

Legacy incremental migration superseded by 20260527_0001.
"""
from collections.abc import Sequence

revision: str = 'ffc086ad1de9'
down_revision: str | None = 'c85a9b5d0c65'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
