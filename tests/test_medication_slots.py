from datetime import datetime

from services.medication_slots import get_nearest_slot


def test_get_nearest_slot_rolls_hour_after_last_separator() -> None:
    slot = get_nearest_slot(datetime(2026, 10, 10, 22, 53))
    assert slot == datetime(2026, 10, 10, 23, 0)


def test_get_nearest_slot_snaps_down_to_quarter_hour() -> None:
    slot = get_nearest_slot(datetime(2026, 10, 10, 8, 20))
    assert slot == datetime(2026, 10, 10, 8, 15)
