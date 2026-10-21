from database.models import MedicationCourse
from services.notes_formatters import (
    build_seizure_display,
    format_medication_courses,
    parse_location_coords,
)


def test_build_seizure_display_includes_profile_name() -> None:
    payload = build_seizure_display(
        seizure_id=1,
        current_profile="Основной",
        date="2026-05-27",
        time="12:00",
        count=1,
        triggers=None,
        severity="3",
        duration="2 мин.",
        comment=None,
        symptoms=None,
        video_tg_id=None,
    )
    assert "Основной" in payload.text
    assert "/delete_1" in payload.text
    assert "нет активного курса" in payload.text
    assert "/update_medication_" not in payload.text


def test_journal_card_lists_passed_medication_without_edit_command() -> None:
    payload = build_seizure_display(
        seizure_id=4,
        current_profile="Основной",
        date="2026-10-11",
        time="01:05",
        count=1,
        triggers=None,
        severity=None,
        duration="1 мин.",
        comment=None,
        symptoms=None,
        video_tg_id=None,
        medication="Ламотриджин, 100 мг, 2 раза в день",
        edit_mode=True,
    )
    assert "Ламотриджин, 100 мг, 2 раза в день" in payload.text
    assert "/update_medication_4" not in payload.text


def test_format_medication_courses_joins_name_dosage_and_frequency() -> None:
    text = format_medication_courses(
        [
            MedicationCourse(
                medication_name="Ламотриджин",
                dosage="100 мг",
                frequency="2 раза в день",
            )
        ]
    )
    assert text == "Ламотриджин, 100 мг, 2 раза в день"
    assert format_medication_courses([]) == "нет активного курса"


def test_parse_location_coords_returns_float_pair() -> None:
    assert parse_location_coords("55.7|37.6") == (55.7, 37.6)
    assert parse_location_coords("home") is None
