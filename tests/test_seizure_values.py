from datetime import date, time

from database.seizure_values import (
    format_seizure_date,
    format_seizure_time,
    parse_seizure_date,
    parse_seizure_time,
)
from use_cases.analytics import SeizurePoint, _month_counts


def test_parse_seizure_clock_keeps_valid_values_and_drops_garbage():
    assert parse_seizure_date("2026-10-11") == date(2026, 10, 11)
    assert parse_seizure_date("не дата") is None
    assert parse_seizure_time("07:45") == time(7, 45)
    assert parse_seizure_time("утром") is None
    assert format_seizure_date(date(2026, 10, 11)) == "2026-10-11"
    assert format_seizure_time(time(7, 45)) == "07:45"


def test_month_counts_bucket_points_by_calendar_month():
    points = [
        SeizurePoint(date(2026, 3, 1), None, None),
        SeizurePoint(date(2026, 3, 2), None, None),
        SeizurePoint(date(2025, 3, 2), None, None),
    ]
    assert _month_counts(points, 2026)[2] == 2
    assert _month_counts(points, 2026)[0] == 0
