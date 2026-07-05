from services.notes_formatters import build_seizure_display, parse_location_coords


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


def test_parse_location_coords_returns_float_pair() -> None:
    assert parse_location_coords("55.7|37.6") == (55.7, 37.6)
    assert parse_location_coords("home") is None
