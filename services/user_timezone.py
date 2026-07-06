from datetime import datetime, timedelta, timezone


def get_local_time_from_offset(offset_hours: int) -> datetime:
    offset = timezone(timedelta(hours=offset_hours))
    return datetime.now(timezone.utc).astimezone(offset)


def get_time_with_minutes_offset(local_datetime: datetime, offset_minutes: int) -> datetime:
    return local_datetime - timedelta(minutes=offset_minutes)
