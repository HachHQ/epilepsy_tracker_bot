import logging
from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from database.redis_query import (
    delete_redis_cached_login,
    get_redis_cached_login,
    get_redis_cached_profiles_list,
    get_redis_cached_user_id_from_db,
    get_redis_global_symptoms_list,
    get_redis_global_triggers_list,
    get_redis_sending_timeout_ten_min,
    get_redis_symptoms_list_by_profile,
    get_redis_triggers_list_by_profile,
    get_redis_trusted_persons,
    get_redis_user_timezone,
    register_trusted_lookup,
    set_redis_cached_current_profile,
    set_redis_cached_login,
    set_redis_cached_profiles_list,
    set_redis_cached_user_id_from_db,
    set_redis_global_symptoms_list,
    set_redis_global_triggers_list,
    set_redis_sending_timeout_ten_min,
    set_redis_symptoms_list_by_profile,
    set_redis_triggers_list_by_profile,
    set_redis_trusted_persons,
    set_redis_user_timezone,
)
from database.repositories.profiles import list_user_profiles, resolve_profile_access
from database.repositories.symptoms_triggers import (
    list_global_symptoms,
    list_global_triggers,
    list_profile_symptoms,
    list_profile_triggers,
)
from database.repositories.trusted_persons import (
    list_trusted_persons_for_owner,
    list_trusted_profiles_for_guest,
)
from database.repositories.users import get_user_by_chat_id
from services.profile_ref import ProfileRef

logger = logging.getLogger(__name__)

# Get operations
async def get_cached_login(session: AsyncSession, user_id: int) -> str | None:
    login = await get_redis_cached_login(user_id)

    if login:
        logger.debug("Get login from Redis")
        return login

    user = await get_user_by_chat_id(session, user_id)
    if not user:
        return None
    login = user.login
    await set_redis_cached_login(user_id, login)
    logger.debug("Get login from DB")

    return login

async def get_cached_user_id_from_db(session: AsyncSession, user_id: int) -> int | None:
    user_db_id = await get_redis_cached_user_id_from_db(user_id)

    if user_db_id:
        logger.debug("Get user_db_id from Redis")
        return int(user_db_id)

    user = await get_user_by_chat_id(session, user_id)
    if not user:
        return None
    user_db_id = user.id
    await set_redis_cached_user_id_from_db(user_id, user_db_id)
    logger.debug("Get user_db_id from DB")

    return user_db_id

async def get_cached_current_profile(session: AsyncSession, user_id: int) -> ProfileRef | None:
    user = await get_user_by_chat_id(session, user_id)
    if user is None or user.current_profile is None:
        return None
    access = await resolve_profile_access(session, user, int(user.current_profile))
    if access is None:
        return None
    await set_redis_cached_current_profile(user_id, access.id, access.name)
    return access


async def remember_login(user_id: int, login: str) -> None:
    await set_redis_cached_login(user_id, login)


async def forget_login(chat_id: int) -> None:
    await delete_redis_cached_login(chat_id)


async def remember_current_profile(chat_id: int, profile_id: int, profile_name: str) -> None:
    await set_redis_cached_current_profile(chat_id, profile_id, profile_name)


async def remember_profiles_list(chat_id: int, profile_type: str, profiles) -> None:
    await set_redis_cached_profiles_list(chat_id, profile_type, profiles)


async def get_trusted_request_cooldown(user_id: int) -> str | None:
    return await get_redis_sending_timeout_ten_min(user_id)


async def remember_trusted_request_cooldown(user_id: int, value: str) -> None:
    await set_redis_sending_timeout_ten_min(user_id, value)


async def count_trusted_lookup(user_id: int) -> int:
    return await register_trusted_lookup(user_id)

async def get_cached_profiles_list(
    session: AsyncSession, user_id: int, profile_type: str = "user_own"
) -> list[dict] | None:
    cached_profiles = await get_redis_cached_profiles_list(user_id, profile_type)
    if cached_profiles:
        logger.debug("Get profiles list from Redis")
        return cached_profiles
    profiles = []
    if profile_type == "trusted":
        profiles = await list_trusted_profiles_for_guest(session, user_id)
    elif profile_type == "user_own":
        profiles = await list_user_profiles(session, user_id)
    if not profiles:
        return None
    logger.debug("Get profiles list from DB")
    await set_redis_cached_profiles_list(user_id=user_id, profile_type=profile_type, profiles=profiles)
    return profiles

async def get_cached_user_timezone(session: AsyncSession, user_id: int):
    user_timezone = await get_redis_user_timezone(user_id)
    if user_timezone:
        logger.debug("Get user timezone from Redis")
        return user_timezone
    user = await get_user_by_chat_id(session, user_id)
    if user is None:
        return None
    await set_redis_user_timezone(user_id, user.timezone)
    logger.debug("Get user timezone from DB")
    return user.timezone

async def get_user_local_datetime(session: AsyncSession, user_id: int):
    user_timezone = await get_cached_user_timezone(session, user_id)
    offset = timezone(timedelta(hours=int(user_timezone)))
    return datetime.now(UTC).astimezone(offset)

async def get_cached_trusted_persons_agrigated_data(session: AsyncSession, user_id: int):
    trusted_persons_redis = await get_redis_trusted_persons(user_id)
    if trusted_persons_redis:
        logger.debug("Get trusted persons aggregated data from Redis")
        return trusted_persons_redis

    trusted_persons_db = await list_trusted_persons_for_owner(session, user_id)
    if trusted_persons_db is None:
        return None

    await set_redis_trusted_persons(user_id, trusted_persons_db)
    logger.debug("Get trusted persons aggregated data from DB")
    return trusted_persons_db


async def get_cached_symptoms_list(session: AsyncSession, user_id: int):
    redis_symptoms = await get_redis_global_symptoms_list(user_id)
    if redis_symptoms:
        logger.debug("Get global symptoms from Redis")
        return redis_symptoms
    symptoms_db = await list_global_symptoms(session)
    await set_redis_global_symptoms_list(user_id, symptoms_db)
    logger.debug("Get global symptoms from DB")
    return symptoms_db

async def get_cached_triggers_list(session: AsyncSession, user_id: int):
    redis_triggers = await get_redis_global_triggers_list(user_id)
    if redis_triggers:
        logger.debug("Get global triggers from Redis")
        return redis_triggers
    triggers_db = await list_global_triggers(session)
    await set_redis_global_triggers_list(user_id, triggers_db)
    logger.debug("Get global triggers from DB")
    return triggers_db

async def get_cached_profile_symptoms_list(session: AsyncSession, user_id: int, profile_id: int):
    redis_profile_symptoms = await get_redis_symptoms_list_by_profile(user_id, profile_id)
    if redis_profile_symptoms:
        logger.debug("Get profile symptoms from Redis")
        return redis_profile_symptoms
    profile_symptoms_db = await list_profile_symptoms(session, profile_id)
    if profile_symptoms_db is None:
        return []
    await set_redis_symptoms_list_by_profile(user_id, profile_id, profile_symptoms_db)
    logger.debug("Get profile symptoms from DB")
    return profile_symptoms_db
async def get_cached_profile_triggers_list(session: AsyncSession, user_id: int, profile_id: int):
    redis_profile_triggers = await get_redis_triggers_list_by_profile(user_id, profile_id)
    if redis_profile_triggers:
        logger.debug("Get profile triggers from Redis")
        return redis_profile_triggers
    profile_triggers_db = await list_profile_triggers(session, profile_id)
    if profile_triggers_db is None:
        return []
    await set_redis_triggers_list_by_profile(user_id, profile_id, profile_triggers_db)
    logger.debug("Get profile triggers from DB")
    return profile_triggers_db