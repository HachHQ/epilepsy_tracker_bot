from datetime import UTC, datetime, timedelta

from config_data.retention import SEIZURE_RETENTION_DAYS, retention_deadline


def test_retention_deadline_uses_default_days() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    deadline = retention_deadline(from_time=start)
    assert deadline == start + timedelta(days=SEIZURE_RETENTION_DAYS)


def test_retention_deadline_accepts_custom_days() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    deadline = retention_deadline(days=30, from_time=start)
    assert deadline == start + timedelta(days=30)
