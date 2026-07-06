"""User soft-delete and data retention deadline.

Revision ID: 20260706_0002
Revises: 20260706_0001
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260706_0002"
down_revision: str | None = "20260706_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("data_retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    op.create_index("ix_users_data_retention_until", "users", ["data_retention_until"])


def downgrade() -> None:
    op.drop_index("ix_users_data_retention_until", table_name="users")
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_column("users", "data_retention_until")
    op.drop_column("users", "deleted_at")
