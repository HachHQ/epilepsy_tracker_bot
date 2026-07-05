from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select, update

from database.models import Profile, Seizure, User
from database.repositories.profiles import list_restorable_profiles, list_user_profiles
from database.repositories.retention import purge_expired_data
from use_cases.profiles import RestoreProfileResult, restore_profile_record
from use_cases.users import SoftDeleteAccountResult, restore_account, soft_delete_account

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_restore_profile_after_soft_delete(db_session, test_user) -> None:
    from use_cases.profiles import delete_profile_record

    with patch("use_cases.profiles.invalidate_after_profile_deleted", new=AsyncMock()), patch(
        "use_cases.profiles.sync_user_own_profiles_cache", new=AsyncMock()
    ):
        await delete_profile_record(
            db_session,
            chat_id=test_user["chat_id"],
            profile_id=test_user["profile"].id,
        )

    restorable = await list_restorable_profiles(db_session, test_user["chat_id"])
    assert len(restorable) == 1

    with patch("use_cases.profiles.sync_user_own_profiles_cache", new=AsyncMock()):
        result = await restore_profile_record(
            db_session,
            chat_id=test_user["chat_id"],
            profile_id=test_user["profile"].id,
        )

    assert result == RestoreProfileResult(
        restored=True, profile_name=test_user["profile"].profile_name,
    )

    profile = await db_session.get(Profile, test_user["profile"].id)
    assert profile.deleted_at is None
    assert profile.seizures_retention_until is None

    profiles = await list_user_profiles(db_session, test_user["chat_id"])
    assert len(profiles) == 1

    seizure = await db_session.scalar(
        select(Seizure).where(Seizure.profile_id == test_user["profile"].id)
    )
    if seizure:
        assert seizure.owner_user_id is None
        assert seizure.retention_until is None


@pytest.mark.asyncio
async def test_soft_delete_and_restore_account(db_session, test_user) -> None:
    with patch("use_cases.users.invalidate_user_debug_cache", new=AsyncMock()), patch(
        "use_cases.users.delete_redis_cached_login", new=AsyncMock()
    ):
        delete_result = await soft_delete_account(
            db_session, chat_id=test_user["chat_id"],
        )

    assert delete_result == SoftDeleteAccountResult(deleted=True)

    user = await db_session.get(User, test_user["user"].id)
    assert user.deleted_at is not None
    assert user.data_retention_until is not None
    assert user.keyword_hash is None

    profile = await db_session.get(Profile, test_user["profile"].id)
    assert profile.deleted_at is not None

    with patch("use_cases.users.set_redis_cached_login", new=AsyncMock()):
        restore_result = await restore_account(
            db_session,
            chat_id=test_user["chat_id"],
            keyword_hash=test_user["user"].keyword_hash or "restored_hash",
        )

    assert restore_result.restored is True
    assert restore_result.profiles_restored >= 1

    user = await db_session.get(User, test_user["user"].id)
    assert user.deleted_at is None


@pytest.mark.asyncio
async def test_purge_expired_seizures(db_session, test_user) -> None:
    from database.repositories.seizures import create_seizure
    from use_cases.profiles import delete_profile_record

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
        await delete_profile_record(
            db_session,
            chat_id=test_user["chat_id"],
            profile_id=test_user["profile"].id,
        )

    past = datetime.now(UTC) - timedelta(days=1)
    await db_session.execute(
        update(Seizure)
        .where(Seizure.profile_id == test_user["profile"].id)
        .values(retention_until=past)
    )
    await db_session.flush()

    stats = await purge_expired_data(db_session)
    assert stats.seizures_deleted >= 1

    seizure_count = await db_session.scalar(
        select(func.count()).select_from(Seizure).where(Seizure.profile_id == test_user["profile"].id)
    )
    assert seizure_count == 0


@pytest.mark.asyncio
async def test_purge_expired_user(db_session, test_user) -> None:
    with patch("use_cases.users.invalidate_user_debug_cache", new=AsyncMock()), patch(
        "use_cases.users.delete_redis_cached_login", new=AsyncMock()
    ):
        await soft_delete_account(db_session, chat_id=test_user["chat_id"])

    past = datetime.now(UTC) - timedelta(days=1)
    user = await db_session.get(User, test_user["user"].id)
    user.data_retention_until = past
    await db_session.flush()

    stats = await purge_expired_data(db_session)
    assert stats.users_deleted >= 1

    assert await db_session.get(User, test_user["user"].id) is None
