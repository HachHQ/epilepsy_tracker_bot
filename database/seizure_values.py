from datetime import date, datetime, time


def parse_seizure_date(value: date | datetime | str | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def parse_seizure_time(value: time | datetime | str | None) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    if isinstance(value, time):
        return value.replace(microsecond=0)
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%H:%M").time()
        except ValueError:
            return None
    return None


def format_seizure_date(value: date | datetime | str | None) -> str:
    parsed = parse_seizure_date(value)
    if parsed is not None:
        return parsed.isoformat()
    return value if isinstance(value, str) else ""


def format_seizure_time(value: time | datetime | str | None) -> str:
    if isinstance(value, str) and parse_seizure_time(value) is None:
        return value
    parsed = parse_seizure_time(value)
    return parsed.strftime("%H:%M") if parsed else ""
