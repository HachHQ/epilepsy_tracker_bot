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
async def test_invalidate_after_seizure_update_symptoms_only() -> None:
    with (
        patch(
            "services.cache_invalidation.delete_redis_profile_symptoms_list",
            new=AsyncMock(),
        ) as profile_symptoms,
        patch(
            "services.cache_invalidation.delete_redis_global_symptoms",
            new=AsyncMock(),
        ) as global_symptoms,
        patch(
            "services.cache_invalidation.delete_redis_profile_triggers_list",
            new=AsyncMock(),
        ) as profile_triggers,
        patch(
            "services.cache_invalidation.delete_redis_global_triggers",
            new=AsyncMock(),
        ) as global_triggers,
    ):
        await cache_invalidation.invalidate_after_seizure_update(1, 2, "symptoms")

    profile_symptoms.assert_awaited_once_with(1, 2)
    global_symptoms.assert_awaited_once_with(1)
    profile_triggers.assert_not_awaited()
    global_triggers.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_trusted_persons() -> None:
    with patch(
        "services.cache_invalidation.delete_redis_trusted_persons",
        new=AsyncMock(),
    ) as trusted:
        await cache_invalidation.invalidate_trusted_persons(55)

    trusted.assert_awaited_once_with(55)


@pytest.mark.asyncio
async def test_invalidate_user_debug_cache_without_profile() -> None:
    with (
        patch(
            "services.cache_invalidation.invalidate_profile_lists",
            new=AsyncMock(),
        ) as profile_lists,
        patch(
            "services.cache_invalidation.invalidate_current_profile",
            new=AsyncMock(),
        ) as current_profile,
        patch(
            "services.cache_invalidation.delete_redis_cached_login",
            new=AsyncMock(),
        ) as login,
        patch(
            "services.cache_invalidation.invalidate_trusted_persons",
            new=AsyncMock(),
        ) as trusted,
        patch(
            "services.cache_invalidation.invalidate_seizure_caches",
            new=AsyncMock(),
        ) as seizure_caches,
    ):
        await cache_invalidation.invalidate_user_debug_cache(10)

    profile_lists.assert_awaited_once_with(10, "user_own")
    current_profile.assert_awaited_once_with(10)
    login.assert_awaited_once_with(10)
    trusted.assert_awaited_once_with(10)
    seizure_caches.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_user_debug_cache_with_profile() -> None:
    with patch(
        "services.cache_invalidation.invalidate_seizure_caches",
        new=AsyncMock(),
    ) as seizure_caches, patch(
        "services.cache_invalidation.invalidate_profile_lists",
        new=AsyncMock(),
    ), patch(
        "services.cache_invalidation.invalidate_current_profile",
        new=AsyncMock(),
    ), patch(
        "services.cache_invalidation.delete_redis_cached_login",
        new=AsyncMock(),
    ), patch(
        "services.cache_invalidation.invalidate_trusted_persons",
        new=AsyncMock(),
    ):
        await cache_invalidation.invalidate_user_debug_cache(10, profile_id=3)

    seizure_caches.assert_awaited_once_with(10, 3)


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
