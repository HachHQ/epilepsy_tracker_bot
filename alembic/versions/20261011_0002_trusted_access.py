"""Trusted profile link is unique, view-only by default, and valid for a day.

Revision ID: 20261011_0002
Revises: 20261011_0001
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261011_0002"
down_revision: str | None = "20261011_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM trusted_person_profiles AS newer
            USING trusted_person_profiles AS older
            WHERE newer.id > older.id
              AND newer.trusted_person_user_id = older.trusted_person_user_id
              AND newer.profile_id = older.profile_id
            """
        )
    )
    op.create_unique_constraint(
        "uq_trusted_person_profile",
        "trusted_person_profiles",
        ["trusted_person_user_id", "profile_id"],
    )
    op.alter_column(
        "trusted_person_profiles",
        "can_edit",
        server_default=sa.false(),
    )
    op.alter_column(
        "trusted_person_requests",
        "expires_at",
        server_default=sa.text("NOW() + INTERVAL '24 hours'"),
    )


def downgrade() -> None:
    op.alter_column(
        "trusted_person_requests",
        "expires_at",
        server_default=sa.text("NOW() + INTERVAL '10 minutes'"),
    )
    op.alter_column(
        "trusted_person_profiles",
        "can_edit",
        server_default=sa.true(),
    )
    op.drop_constraint("uq_trusted_person_profile", "trusted_person_profiles", type_="unique")
