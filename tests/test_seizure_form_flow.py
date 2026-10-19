from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from handlers_logic.seizure_form.card import format_review, saved_caption
from handlers_logic.seizure_form.helpers import load_symptom_keyboard_options
from handlers_logic.states_factories import SeizureForm
from keyboards.seizure_kb import DURATION_CHOICES, get_enrich_kb, get_year_date_kb


def test_duration_choices_store_interval_midpoints():
    stored = [seconds for seconds, _label in DURATION_CHOICES]
    assert stored == [15, 45, 90, 210, 420]


def test_recent_day_buttons_use_the_given_local_day():
    local = datetime(2026, 10, 11, 1, 30, tzinfo=UTC)
    markup = get_year_date_kb(today=local, action_btns=False)
    callbacks = [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data and button.callback_data.startswith("year:")
    ]
    assert "year:today/2026-10-11" in callbacks
    assert "year:one_d_ago/2026-10-10" in callbacks
    assert "year:two_d_ago/2026-10-09" in callbacks


def test_review_shows_prefilled_type_before_save():
    text = format_review(
        {
            "date_short": "2026-10-11",
            "time_of_day": "01:05",
            "duration": 90,
            "count": 1,
            "type_of_seizure": "Абсанс",
            "severity": "3",
            "triggers": "Свет",
            "from_last": True,
        }
    )
    assert "Абсанс" in text
    assert "01:05" in text
    assert "прошлой записи" in text
    assert "нет активного курса" in text


def test_review_lists_the_course_active_on_the_seizure_day():
    text = format_review(
        {"date_short": "2026-10-11", "time_of_day": "01:05", "duration": 90, "count": 1},
        "Ламотриджин, 100 мг, 2 раза в день",
    )
    assert "Принимаемый курс лекарств:" in text
    assert "Ламотриджин, 100 мг, 2 раза в день" in text


def test_short_form_does_not_stop_on_symptoms():
    assert SeizureForm.symptoms not in SeizureForm.states_sequence


def test_enrich_keyboard_can_open_symptoms():
    markup = get_enrich_kb(4)
    callbacks = [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    ]
    assert "enrich:symptoms:4" in callbacks


def test_saved_card_shows_symptoms():
    seizure = SimpleNamespace(
        date="2026-10-11",
        time="01:05",
        duration=90,
        count=1,
        type_of_seizure=None,
        severity=None,
        triggers=None,
        symptoms="Оцепенение",
        comment=None,
        location=None,
        video_tg_id=None,
    )
    text = saved_caption(seizure)
    assert "Симптомы:" in text
    assert "Оцепенение" in text


@pytest.mark.asyncio
async def test_symptom_keyboard_lists_catalog_and_current_value():
    with patch(
        "handlers_logic.seizure_form.helpers.get_cached_profile_symptoms_list",
        new=AsyncMock(return_value=["Свой симптом"]),
    ):
        names = await load_symptom_keyboard_options(
            AsyncMock(), 1, 2, ["оцепенение", "свой симптом"]
        )
    assert names[0] == "Оцепенение"
    assert names.count("Оцепенение") == 1
    assert "Свой симптом" in names
