"""Store seizure date and time as date and time columns.

Revision ID: 20261011_0001
Revises: 20260706_0002
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261011_0001"
down_revision: str | None = "20260706_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE seizures
            ALTER COLUMN "date" TYPE date
            USING (
                CASE
                    WHEN "date" ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN "date"::date
                    ELSE NULL
                END
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE seizures
            ALTER COLUMN "time" TYPE time
            USING (
                CASE
                    WHEN "time" ~ '^[0-9]{2}:[0-9]{2}(:[0-9]{2})?$' THEN "time"::time
                    ELSE NULL
                END
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE seizures
            ALTER COLUMN "time" TYPE varchar(25)
            USING to_char("time", 'HH24:MI')
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE seizures
            ALTER COLUMN "date" TYPE varchar(25)
            USING to_char("date", 'YYYY-MM-DD')
            """
        )
    )
