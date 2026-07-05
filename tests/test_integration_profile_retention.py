from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from database.models import Profile, Seizure
from database.repositories.profiles import get_active_profile_by_id, list_user_profiles
from use_cases.profiles import DeleteProfileResult, delete_profile_record

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_soft_delete_preserves_seizures(db_session, test_user) -> None:
    from database.repositories.seizures import create_seizure

    await create_seizure(
        db_session,
        profile_id=test_user["profile"].id,
        date="2026-05-01",
        time=None,
        severity="1",
        duration=None,
        comment=None,
        count=1,
        video_tg_id=None,
        trigger_names=None,
        symptom_names=None,
        location=None,
        creator_login=test_user["user"].login,
        type_of_seizure=None,
    )
    await db_session.flush()

    with patch("use_cases.profiles.invalidate_after_profile_deleted", new=AsyncMock()), patch(
        "use_cases.profiles.sync_user_own_profiles_cache", new=AsyncMock()
    ):
        result = await delete_profile_record(
            db_session,
            chat_id=test_user["chat_id"],
            profile_id=test_user["profile"].id,
        )

    assert result == DeleteProfileResult(deleted=True, seizures_preserved=1)

    profile = await db_session.get(Profile, test_user["profile"].id)
    assert profile is not None
    assert profile.deleted_at is not None
    assert profile.seizures_retention_until is not None

    assert await get_active_profile_by_id(db_session, test_user["profile"].id) is None

    seizure_count = await db_session.scalar(
        select(func.count()).select_from(Seizure).where(Seizure.profile_id == test_user["profile"].id)
    )
    assert seizure_count == 1

    seizure = await db_session.scalar(
        select(Seizure).where(Seizure.profile_id == test_user["profile"].id)
    )
    assert seizure.owner_user_id == test_user["user"].id
    assert seizure.retention_until is not None


@pytest.mark.asyncio
async def test_deleted_profile_hidden_from_list(db_session, test_user) -> None:
    with patch("use_cases.profiles.invalidate_after_profile_deleted", new=AsyncMock()), patch(
        "use_cases.profiles.sync_user_own_profiles_cache", new=AsyncMock()
    ):
        await delete_profile_record(
            db_session,
            chat_id=test_user["chat_id"],
            profile_id=test_user["profile"].id,
        )

    profiles = await list_user_profiles(db_session, test_user["chat_id"])
    assert profiles == []
