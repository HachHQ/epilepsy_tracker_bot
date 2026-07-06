from unittest.mock import AsyncMock, patch

import pytest

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
