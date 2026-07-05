from datetime import UTC, datetime, timedelta

# How long seizure records stay recoverable after profile deletion.
SEIZURE_RETENTION_DAYS = 180

# How long a soft-deleted user account and its data remain recoverable.
USER_DATA_RETENTION_DAYS = 180


def retention_deadline(
    *,
    days: int = SEIZURE_RETENTION_DAYS,
    from_time: datetime | None = None,
) -> datetime:
    start = from_time or datetime.now(UTC)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return start + timedelta(days=days)
