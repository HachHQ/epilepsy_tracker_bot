"""initial schema

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260527_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

request_status = postgresql.ENUM(
    "PENDING",
    "ACCEPTED",
    "REJECTED",
    "EXPIRED",
    name="requeststatus",
    create_type=False,
)


def upgrade() -> None:
    request_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("telegram_fullname", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=25), nullable=True),
        sa.Column("login", sa.String(length=25), nullable=False),
        sa.Column("timezone", sa.String(length=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("keyword_hash", sa.String(length=60), nullable=True),
        sa.Column("current_profile", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("login"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_name", sa.String(length=40), nullable=False),
        sa.Column("type_of_epilepsy", sa.String(length=100), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=20), nullable=True),
        sa.Column("biological_species", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"])

    op.create_table(
        "seizures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.String(length=25), nullable=True),
        sa.Column("time", sa.String(length=25), nullable=True),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("comment", sa.String(length=150), nullable=True),
        sa.Column("count", sa.Integer(), nullable=True),
        sa.Column("video_tg_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("creator_login", sa.String(length=25), nullable=False),
        sa.Column("type_of_seizure", sa.String(length=50), nullable=True),
        sa.Column("triggers", sa.String(), nullable=True),
        sa.Column("location", sa.String(length=30), nullable=True),
        sa.Column("symptoms", sa.String(), nullable=True),
    )
    op.create_index("ix_seizures_profile_id_date", "seizures", ["profile_id", "date"])

    op.create_table(
        "symptoms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symptom_name", sa.String(length=100), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True),
        sa.UniqueConstraint("symptom_name", "profile_id", name="uix_symptom_name_profile"),
    )

    op.create_table(
        "triggers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trigger_name", sa.String(length=100), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True),
        sa.UniqueConstraint("trigger_name", "profile_id", name="uix_trigger_name_profile"),
    )

    op.create_table(
        "seizure_symptoms",
        sa.Column("seizure_id", sa.Integer(), sa.ForeignKey("seizures.id", ondelete="CASCADE")),
        sa.Column("symptom_id", sa.Integer(), sa.ForeignKey("symptoms.id", ondelete="CASCADE")),
        sa.PrimaryKeyConstraint("seizure_id", "symptom_id"),
    )

    op.create_table(
        "seizure_triggers",
        sa.Column("seizure_id", sa.Integer(), sa.ForeignKey("seizures.id", ondelete="CASCADE")),
        sa.Column("trigger_id", sa.Integer(), sa.ForeignKey("triggers.id", ondelete="CASCADE")),
        sa.PrimaryKeyConstraint("seizure_id", "trigger_id"),
    )

    op.create_table(
        "trusted_person_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trusted_person_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("profile_owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("can_read", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("can_edit", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("get_notification", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_trusted_person_profiles_trusted_user",
        "trusted_person_profiles",
        ["trusted_person_user_id"],
    )
    op.create_index(
        "ix_trusted_person_profiles_owner_profile",
        "trusted_person_profiles",
        ["profile_owner_id", "profile_id"],
    )

    op.create_table(
        "trusted_person_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recepient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("transmitted_profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", request_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), server_default=sa.text("NOW() + INTERVAL '10 minutes'"), nullable=False),
    )

    op.create_table(
        "user_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notify_time", sa.Time(), nullable=False),
        sa.Column("note", sa.String(length=100), nullable=False),
        sa.Column("pattern", sa.String(length=20), nullable=False, server_default="daily"),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "notify_time", name="uix_user_notify_time"),
    )

    op.create_table(
        "medication_courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("medication_name", sa.String(length=100), nullable=True),
        sa.Column("dosage", sa.String(length=50), nullable=True),
        sa.Column("frequency", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.String(length=200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("medication_courses")
    op.drop_table("user_notifications")
    op.drop_table("trusted_person_requests")
    op.drop_index("ix_trusted_person_profiles_owner_profile", table_name="trusted_person_profiles")
    op.drop_index("ix_trusted_person_profiles_trusted_user", table_name="trusted_person_profiles")
    op.drop_table("trusted_person_profiles")
    op.drop_table("seizure_triggers")
    op.drop_table("seizure_symptoms")
    op.drop_table("triggers")
    op.drop_table("symptoms")
    op.drop_index("ix_seizures_profile_id_date", table_name="seizures")
    op.drop_table("seizures")
    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_table("profiles")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
    request_status.drop(op.get_bind(), checkfirst=True)
