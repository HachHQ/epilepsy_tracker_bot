from unittest.mock import AsyncMock, patch

import pytest

from use_cases import profiles as profile_use_cases


@pytest.mark.asyncio
async def test_update_profile_field_refreshes_profiles_cache() -> None:
    fake_profile = object()
    with patch(
        "use_cases.profiles.update_profile_attribute",
        new=AsyncMock(return_value=fake_profile),
    ), patch(
        "use_cases.profiles.sync_user_own_profiles_cache",
        new=AsyncMock(),
    ) as sync_mock:
        result = await profile_use_cases.update_profile_field(
            session=AsyncMock(),
            chat_id=1,
            profile_id=5,
            attribute="age",
            new_value=30,
        )

    assert result is fake_profile
    sync_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_switch_current_profile_updates_db_and_redis() -> None:
    with patch(
        "use_cases.profiles.get_active_profile_by_id",
        new=AsyncMock(return_value=object()),
    ), patch(
        "use_cases.profiles.set_user_current_profile",
        new=AsyncMock(return_value=object()),
    ), patch(
        "use_cases.profiles.set_redis_cached_current_profile",
        new=AsyncMock(),
    ) as redis_mock:
        result = await profile_use_cases.switch_current_profile(
            session=AsyncMock(),
            chat_id=10,
            profile_id=3,
            profile_name="Основной",
        )

    assert result.switched is True
    redis_mock.assert_awaited_once_with(10, profile_id=3, profile_name="Основной")


@pytest.mark.asyncio
async def test_delete_profile_record_soft_deletes_and_syncs_cache() -> None:
    with patch(
        "use_cases.profiles.soft_delete_profile",
        new=AsyncMock(return_value=3),
    ), patch(
        "use_cases.profiles.invalidate_after_profile_deleted",
        new=AsyncMock(),
    ) as invalidate_mock, patch(
        "use_cases.profiles.sync_user_own_profiles_cache",
        new=AsyncMock(),
    ) as sync_mock:
        result = await profile_use_cases.delete_profile_record(
            session=AsyncMock(),
            chat_id=42,
            profile_id=7,
        )

    assert result.deleted is True
    assert result.seizures_preserved == 3
    invalidate_mock.assert_awaited_once_with(42)
    sync_mock.assert_awaited_once()
