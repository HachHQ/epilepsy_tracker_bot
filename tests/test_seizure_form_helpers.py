from datetime import UTC, datetime

from services.user_timezone import get_local_time_from_offset, get_time_with_minutes_offset


def test_get_local_time_from_offset_returns_aware_datetime() -> None:
    local_time = get_local_time_from_offset(3)
    assert local_time.tzinfo is not None


def test_get_time_with_minutes_offset_subtracts_minutes() -> None:
    base = datetime(2026, 5, 27, 12, 30, tzinfo=UTC)
    shifted = get_time_with_minutes_offset(base, 15)
    assert shifted.minute == 15


def test_parse_callback_data_year_shortcut() -> None:
    from handlers_logic.seizure_form.helpers import parse_callback_data

    parsed = parse_callback_data("year:today/2026-05-27")
    assert parsed["value"] == "today"
    assert parsed["date"] == "2026-05-27"
