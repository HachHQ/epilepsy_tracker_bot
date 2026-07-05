from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from database.models import Seizure, Symptom
from database.repositories.seizures import get_seizure_by_id
from use_cases.seizures import (
    create_seizure_from_state,
    delete_seizure_record,
    update_seizure_field,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_seizure_create_persists_triggers_and_symptoms(db_session, test_user) -> None:
    with patch("use_cases.seizures.invalidate_seizure_caches", new=AsyncMock()):
        preview = await create_seizure_from_state(
            db_session,
            user_id=test_user["chat_id"],
            current_profile=test_user["profile_key"],
            creator_login=test_user["user"].login,
            state_data={
                "date_short": "2026-05-27",
                "time_of_day": "14:30",
                "severity": "2",
                "duration": 120,
                "comment": "integration test",
                "count": 1,
                "selected_triggers": ["Stress"],
                "symptoms": "aura, headache",
            },
        )

    assert preview.seizure_id > 0
    assert preview.triggers == "Stress"
    assert "aura" in preview.symptoms

    symptom_names = (
        await db_session.scalars(
            select(Symptom.symptom_name).where(Symptom.profile_id == test_user["profile"].id)
        )
    ).all()
    assert "aura" in symptom_names
    assert "headache" in symptom_names


@pytest.mark.asyncio
async def test_seizure_update_and_delete(db_session, test_user) -> None:
    with patch("use_cases.seizures.invalidate_seizure_caches", new=AsyncMock()), patch(
        "use_cases.seizures.invalidate_after_seizure_update", new=AsyncMock()
    ):
        preview = await create_seizure_from_state(
            db_session,
            user_id=test_user["chat_id"],
            current_profile=test_user["profile_key"],
            creator_login=test_user["user"].login,
            state_data={"date_short": "2026-06-01", "severity": "1"},
        )

        updated = await update_seizure_field(
            db_session,
            user_id=test_user["chat_id"],
            profile_id=test_user["profile"].id,
            seizure_id=preview.seizure_id,
            attribute="severity",
            new_value="4",
        )
        assert updated is not None
        assert updated.severity == "4"

        deleted = await delete_seizure_record(
            db_session,
            user_id=test_user["chat_id"],
            profile_id=test_user["profile"].id,
            seizure_id=preview.seizure_id,
        )

    assert deleted is True
    remaining = await get_seizure_by_id(
        db_session, preview.seizure_id, test_user["profile"].id
    )
    assert remaining is None
