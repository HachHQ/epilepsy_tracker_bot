"""Centralized Redis cache invalidation after data mutations."""

from database.redis_query import (
    delete_redis_cached_current_profile,
    delete_redis_cached_login,
    delete_redis_cached_profiles_list,
    delete_redis_global_symptoms,
    delete_redis_global_triggers,
    delete_redis_profile_symptoms_list,
    delete_redis_profile_triggers_list,
    delete_redis_trusted_persons,
)

SEIZURE_TRIGGER_ATTRIBUTES = frozenset({"triggers"})
SEIZURE_SYMPTOM_ATTRIBUTES = frozenset({"symptoms"})


async def invalidate_seizure_caches(user_id: int, profile_id: int) -> None:
    """Invalidate profile/global trigger and symptom lists after seizure changes."""
    await delete_redis_profile_triggers_list(user_id, profile_id)
    await delete_redis_profile_symptoms_list(user_id, profile_id)
    await delete_redis_global_triggers(user_id)
    await delete_redis_global_symptoms(user_id)


async def invalidate_after_seizure_update(
    user_id: int,
    profile_id: int,
    attribute: str,
) -> None:
    if attribute in SEIZURE_TRIGGER_ATTRIBUTES:
        await delete_redis_profile_triggers_list(user_id, profile_id)
        await delete_redis_global_triggers(user_id)
        return
    if attribute in SEIZURE_SYMPTOM_ATTRIBUTES:
        await delete_redis_profile_symptoms_list(user_id, profile_id)
        await delete_redis_global_symptoms(user_id)


async def invalidate_profile_lists(chat_id: int, profile_type: str = "user_own") -> None:
    await delete_redis_cached_profiles_list(chat_id, profile_type)


async def invalidate_current_profile(chat_id: int) -> None:
    await delete_redis_cached_current_profile(chat_id)


async def invalidate_after_profile_deleted(chat_id: int) -> None:
    await invalidate_current_profile(chat_id)
    await invalidate_profile_lists(chat_id, "user_own")


async def invalidate_trusted_persons(chat_id: int) -> None:
    await delete_redis_trusted_persons(chat_id)


async def invalidate_user_debug_cache(chat_id: int, profile_id: int | None = None) -> None:
    """Clear cached session data for admin debug command."""
    await invalidate_profile_lists(chat_id, "user_own")
    await invalidate_current_profile(chat_id)
    await delete_redis_cached_login(chat_id)
    await invalidate_trusted_persons(chat_id)
    if profile_id is not None:
        await invalidate_seizure_caches(chat_id, profile_id)
