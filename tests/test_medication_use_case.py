from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from database.models import MedicationCourse
from use_cases import medications as medication_use_cases


@pytest.mark.asyncio
async def test_create_course_from_form_delegates_to_repository() -> None:
    fake_course = object()
    with patch(
        "use_cases.medications.create_medication_course",
        new=AsyncMock(return_value=fake_course),
    ) as create_mock:
        result = await medication_use_cases.create_course_from_form(
            session=AsyncMock(),
            profile_id=7,
            medication_name="Keppra",
            dosage="500mg",
            frequency="2x",
            notes=None,
            start_date="2026-01-01",
            end_date=None,
        )

    assert result.course is fake_course
    create_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_course_field_returns_not_found() -> None:
    with patch(
        "use_cases.medications.update_medication_attribute",
        new=AsyncMock(return_value=None),
    ):
        result = await medication_use_cases.update_course_field(
            session=AsyncMock(),
            profile_id=1,
            medication_id=99,
            attribute="dosage",
            new_value="250mg",
        )

    assert result.updated is False
    assert result.course is None


@pytest.mark.asyncio
async def test_delete_course_returns_deleted_flag() -> None:
    with patch(
        "use_cases.medications.delete_medication",
        new=AsyncMock(return_value=True),
    ):
        result = await medication_use_cases.delete_course(
            session=AsyncMock(),
            profile_id=1,
            medication_id=3,
        )

    assert result.deleted is True


def test_courses_active_on_uses_the_seizure_day() -> None:
    started_earlier = MedicationCourse(
        id=2,
        medication_name="Ламотриджин",
        dosage="100 мг",
        frequency="2 раза в день",
        start_date=date(2026, 1, 1),
        end_date=None,
    )
    ended_yesterday = MedicationCourse(
        id=1,
        medication_name="Кеппра",
        dosage="500 мг",
        frequency="утро",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 10, 10),
    )
    starts_tomorrow = MedicationCourse(
        id=3,
        medication_name="Позже",
        start_date=date(2026, 10, 12),
        end_date=None,
    )
    missing_start = MedicationCourse(id=4, medication_name="Без даты", start_date=None)
    ends_today = MedicationCourse(
        id=5,
        medication_name="Карбамазепин",
        dosage="200 мг",
        frequency="вечер",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 10, 11),
    )

    active = medication_use_cases.courses_active_on(
        [ended_yesterday, starts_tomorrow, started_earlier, missing_start, ends_today],
        date(2026, 10, 11),
    )

    assert [course.medication_name for course in active] == ["Ламотриджин", "Карбамазепин"]


@pytest.mark.asyncio
async def test_medication_text_on_lists_active_courses() -> None:
    course = MedicationCourse(
        id=1,
        medication_name="Ламотриджин",
        dosage="100 мг",
        frequency="2 раза в день",
        start_date=date(2026, 1, 1),
        end_date=None,
    )
    with patch(
        "use_cases.medications.list_profile_medications",
        new=AsyncMock(return_value=[course]),
    ):
        text = await medication_use_cases.medication_text_on(AsyncMock(), 7, "2026-10-11")

    assert text == "Ламотриджин, 100 мг, 2 раза в день"
