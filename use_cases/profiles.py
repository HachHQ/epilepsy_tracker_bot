from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import SEIZURE_RETENTION_DAYS
from database.models import Profile
from database.redis_query import set_redis_cached_current_profile, set_redis_cached_profiles_list
from database.repositories.profiles import (
    create_profile,
    get_active_profile_by_id,
    list_restorable_profiles,
    list_user_profiles,
    restore_profile,
    set_user_current_profile,
    soft_delete_profile,
    update_profile_attribute,
)
from database.repositories.retention import purge_profile_forever
from database.repositories.users import get_user_by_chat_id
from services.cache_invalidation import invalidate_after_profile_deleted


@dataclass(frozen=True)
class CreateProfileResult:
    created: bool
    profile_name: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class SwitchProfileResult:
    switched: bool
    reason: str | None = None


@dataclass(frozen=True)
class DeleteProfileResult:
    deleted: bool
    seizures_preserved: int = 0
    retention_days: int = SEIZURE_RETENTION_DAYS


@dataclass(frozen=True)
class RestoreProfileResult:
    restored: bool
    profile_name: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class PurgeProfileResult:
    purged: bool
    reason: str | None = None


async def sync_user_own_profiles_cache(session: AsyncSession, chat_id: int) -> None:
    profiles = await list_user_profiles(session, chat_id)
    await set_redis_cached_profiles_list(chat_id, "user_own", profiles)


async def create_profile_from_form(
    session: AsyncSession,
    *,
    chat_id: int,
    form_data: dict,
) -> CreateProfileResult:
    user = await get_user_by_chat_id(session, chat_id)
    if not user:
        return CreateProfileResult(created=False, reason="user_not_found")

    profile = await create_profile(
        session,
        user=user,
        profile_name=form_data["profile_name"],
        type_of_epilepsy=form_data.get("type_of_epilepsy"),
        age=int(form_data["age"]),
        sex=form_data["sex"],
        biological_species=form_data.get("animal_species"),
    )
    await sync_user_own_profiles_cache(session, chat_id)
    return CreateProfileResult(created=True, profile_name=profile.profile_name)


async def get_profile(session: AsyncSession, profile_id: int) -> Profile | None:
    return await get_active_profile_by_id(session, profile_id)


async def update_profile_field(
    session: AsyncSession,
    *,
    chat_id: int,
    profile_id: int,
    attribute: str,
    new_value,
) -> Profile | None:
    profile = await update_profile_attribute(session, profile_id, attribute, new_value)
    if profile is not None:
        await sync_user_own_profiles_cache(session, chat_id)
    return profile


async def delete_profile_record(
    session: AsyncSession,
    *,
    chat_id: int,
    profile_id: int,
) -> DeleteProfileResult:
    preserved = await soft_delete_profile(session, profile_id)
    if preserved is None:
        return DeleteProfileResult(deleted=False)

    await invalidate_after_profile_deleted(chat_id)
    await sync_user_own_profiles_cache(session, chat_id)
    return DeleteProfileResult(deleted=True, seizures_preserved=preserved)


async def switch_current_profile(
    session: AsyncSession,
    *,
    chat_id: int,
    profile_id: int,
    profile_name: str,
) -> SwitchProfileResult:
    profile = await get_active_profile_by_id(session, profile_id)
    if not profile:
        return SwitchProfileResult(switched=False, reason="profile_not_found")

    user = await set_user_current_profile(session, chat_id, profile_id)
    if not user:
        return SwitchProfileResult(switched=False, reason="user_not_found")

    await set_redis_cached_current_profile(chat_id, profile_id=profile_id, profile_name=profile_name)
    return SwitchProfileResult(switched=True)


async def list_restorable_profile_records(
    session: AsyncSession,
    chat_id: int,
) -> list[dict]:
    return await list_restorable_profiles(session, chat_id)


async def restore_profile_record(
    session: AsyncSession,
    *,
    chat_id: int,
    profile_id: int,
) -> RestoreProfileResult:
    from database.repositories.profiles import get_restorable_profile_for_user

    profile = await get_restorable_profile_for_user(
        session, chat_id=chat_id, profile_id=profile_id,
    )
    if not profile:
        return RestoreProfileResult(restored=False, reason="not_restorable")

    restored = await restore_profile(session, profile_id)
    if not restored:
        return RestoreProfileResult(restored=False, reason="restore_failed")

    await sync_user_own_profiles_cache(session, chat_id)
    return RestoreProfileResult(restored=True, profile_name=profile.profile_name)


async def purge_profile_forever_record(
    session: AsyncSession,
    *,
    chat_id: int,
    profile_id: int,
) -> PurgeProfileResult:
    purged = await purge_profile_forever(session, chat_id=chat_id, profile_id=profile_id)
    if not purged:
        return PurgeProfileResult(purged=False, reason="not_found")

    await invalidate_after_profile_deleted(chat_id)
    await sync_user_own_profiles_cache(session, chat_id)
    return PurgeProfileResult(purged=True)
