import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_nearest_slot(dt: datetime) -> datetime:
    separators = [7, 22, 37, 52]
    minute = dt.minute
    if minute <= separators[0]:
        slot_minute = 0
    elif minute <= separators[1]:
        slot_minute = 15
    elif minute <= separators[2]:
        slot_minute = 30
    elif minute <= separators[3]:
        slot_minute = 45
    else:
        return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return dt.replace(minute=slot_minute, second=0, microsecond=0)


def convert_utc_to_user_time(utc_dt: datetime, tz_offset_str: str | None) -> datetime:
    try:
        return utc_dt + timedelta(hours=int(tz_offset_str or 0))
    except ValueError:
        logger.warning("Invalid timezone offset %r; falling back to UTC", tz_offset_str)
        return utc_dt
