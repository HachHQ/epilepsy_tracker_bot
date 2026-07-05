from unittest.mock import AsyncMock, patch

import pytest

from services import cache_invalidation


@pytest.mark.asyncio
async def test_invalidate_seizure_caches_clears_profile_and_global_lists() -> None:
    with (
        patch(
            "services.cache_invalidation.delete_redis_profile_triggers_list",
            new=AsyncMock(),
        ) as profile_triggers,
        patch(
            "services.cache_invalidation.delete_redis_profile_symptoms_list",
            new=AsyncMock(),
        ) as profile_symptoms,
        patch(
            "services.cache_invalidation.delete_redis_global_triggers",
            new=AsyncMock(),
        ) as global_triggers,
        patch(
            "services.cache_invalidation.delete_redis_global_symptoms",
            new=AsyncMock(),
        ) as global_symptoms,
    ):
        await cache_invalidation.invalidate_seizure_caches(42, 7)

    profile_triggers.assert_awaited_once_with(42, 7)
    profile_symptoms.assert_awaited_once_with(42, 7)
    global_triggers.assert_awaited_once_with(42)
    global_symptoms.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_invalidate_after_seizure_update_triggers_only() -> None:
    with (
        patch(
            "services.cache_invalidation.delete_redis_profile_triggers_list",
            new=AsyncMock(),
        ) as profile_triggers,
        patch(
            "services.cache_invalidation.delete_redis_global_triggers",
            new=AsyncMock(),
        ) as global_triggers,
        patch(
            "services.cache_invalidation.delete_redis_profile_symptoms_list",
            new=AsyncMock(),
        ) as profile_symptoms,
        patch(
            "services.cache_invalidation.delete_redis_global_symptoms",
            new=AsyncMock(),
        ) as global_symptoms,
    ):
        await cache_invalidation.invalidate_after_seizure_update(1, 2, "triggers")

    profile_triggers.assert_awaited_once_with(1, 2)
    global_triggers.assert_awaited_once_with(1)
    profile_symptoms.assert_not_awaited()
    global_symptoms.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_after_profile_deleted() -> None:
    with (
        patch(
            "services.cache_invalidation.invalidate_current_profile",
            new=AsyncMock(),
        ) as current_profile,
        patch(
            "services.cache_invalidation.invalidate_profile_lists",
            new=AsyncMock(),
        ) as profile_lists,
    ):
        await cache_invalidation.invalidate_after_profile_deleted(99)

    current_profile.assert_awaited_once_with(99)
    profile_lists.assert_awaited_once_with(99, "user_own")
