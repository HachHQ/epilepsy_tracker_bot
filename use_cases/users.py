from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import USER_DATA_RETENTION_DAYS
from database.redis_query import delete_redis_cached_login, set_redis_cached_login
from database.repositories.profiles import list_restorable_profiles, restore_profile
from database.repositories.retention import purge_user_forever
from database.repositories.users import (
    create_user,
    get_deleted_user_by_chat_id,
    get_user_by_chat_id,
    get_user_by_login,
    restore_user,
    soft_delete_user,
)
from services.cache_invalidation import invalidate_user_debug_cache


@dataclass(frozen=True)
class RegisterUserResult:
    created: bool
    reason: str | None = None


@dataclass(frozen=True)
class SoftDeleteAccountResult:
    deleted: bool
    retention_days: int = USER_DATA_RETENTION_DAYS


@dataclass(frozen=True)
class RestoreAccountResult:
    restored: bool
    profiles_restored: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class PurgeAccountResult:
    purged: bool
    reason: str | None = None


@dataclass(frozen=True)
class DeletedAccountInfo:
    can_restore: bool
    retention_until: str | None = None


async def register_user_from_form(
    session: AsyncSession,
    *,
    telegram_id: int,
    telegram_username: str | None,
    telegram_fullname: str | None,
    form_data: dict,
) -> RegisterUserResult:
    if await get_user_by_chat_id(session, telegram_id):
        return RegisterUserResult(created=False, reason="telegram_id_exists")
    if await get_deleted_user_by_chat_id(session, telegram_id):
        return RegisterUserResult(created=False, reason="account_deleted_restore_available")
    if await get_user_by_login(session, form_data["login"]):
        return RegisterUserResult(created=False, reason="login_exists")

    await create_user(
        session,
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        telegram_fullname=telegram_fullname,
        name=form_data["name"],
        login=form_data["login"],
        timezone=form_data["timezone"],
        keyword_hash=form_data["codeword"],
    )
    await set_redis_cached_login(user_id=telegram_id, login=form_data["login"])
    return RegisterUserResult(created=True)


async def get_deleted_account_info(session: AsyncSession, chat_id: int) -> DeletedAccountInfo | None:
    user = await get_deleted_user_by_chat_id(session, chat_id)
    if not user:
        return None

    from datetime import UTC, datetime

    can_restore = bool(
        user.data_retention_until and user.data_retention_until > datetime.now(UTC)
    )
    retention_until = (
        user.data_retention_until.isoformat() if user.data_retention_until else None
    )
    return DeletedAccountInfo(can_restore=can_restore, retention_until=retention_until)


async def soft_delete_account(
    session: AsyncSession,
    *,
    chat_id: int,
) -> SoftDeleteAccountResult:
    user = await get_user_by_chat_id(session, chat_id)
    if not user:
        return SoftDeleteAccountResult(deleted=False)

    deleted = await soft_delete_user(session, user.id)
    if not deleted:
        return SoftDeleteAccountResult(deleted=False)

    await invalidate_user_debug_cache(chat_id)
    await delete_redis_cached_login(chat_id)
    return SoftDeleteAccountResult(deleted=True)


async def restore_account(
    session: AsyncSession,
    *,
    chat_id: int,
    telegram_username: str | None = None,
    telegram_fullname: str | None = None,
    keyword_hash: str | None = None,
) -> RestoreAccountResult:
    user = await restore_user(
        session,
        chat_id,
        telegram_username=telegram_username,
        telegram_fullname=telegram_fullname,
        keyword_hash=keyword_hash,
    )
    if not user:
        return RestoreAccountResult(restored=False, reason="not_restorable")

    restorable = await list_restorable_profiles(session, chat_id)
    profiles_restored = 0
    for profile_data in restorable:
        if await restore_profile(session, profile_data["id"]):
            profiles_restored += 1

    await set_redis_cached_login(user_id=chat_id, login=user.login)
    return RestoreAccountResult(restored=True, profiles_restored=profiles_restored)


async def purge_account_forever(
    session: AsyncSession,
    *,
    chat_id: int,
) -> PurgeAccountResult:
    user = await get_user_by_chat_id(session, chat_id, include_deleted=True)
    if not user:
        return PurgeAccountResult(purged=False, reason="not_found")

    purged = await purge_user_forever(session, user.id)
    if not purged:
        return PurgeAccountResult(purged=False, reason="purge_failed")

    await invalidate_user_debug_cache(chat_id)
    await delete_redis_cached_login(chat_id)
    return PurgeAccountResult(purged=True)
