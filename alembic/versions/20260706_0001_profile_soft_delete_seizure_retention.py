"""Profile soft-delete and seizure retention without cascade wipe.

Revision ID: 20260706_0001
Revises: bc9ff2e0ce8b
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260706_0001"
down_revision: str | None = "bc9ff2e0ce8b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "profiles",
        sa.Column("seizures_retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_profiles_deleted_at", "profiles", ["deleted_at"])

    op.add_column(
        "seizures",
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "seizures",
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_seizures_owner_user_id", "seizures", ["owner_user_id"])
    op.create_index("ix_seizures_retention_until", "seizures", ["retention_until"])

    op.drop_constraint("seizures_profile_id_fkey", "seizures", type_="foreignkey")
    op.create_foreign_key(
        "seizures_profile_id_fkey",
        "seizures",
        "profiles",
        ["profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("seizures_profile_id_fkey", "seizures", type_="foreignkey")
    op.create_foreign_key(
        "seizures_profile_id_fkey",
        "seizures",
        "profiles",
        ["profile_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("ix_seizures_retention_until", table_name="seizures")
    op.drop_index("ix_seizures_owner_user_id", table_name="seizures")
    op.drop_column("seizures", "retention_until")
    op.drop_column("seizures", "owner_user_id")

    op.drop_index("ix_profiles_deleted_at", table_name="profiles")
    op.drop_column("profiles", "seizures_retention_until")
    op.drop_column("profiles", "deleted_at")
