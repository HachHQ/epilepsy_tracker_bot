import logging
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from database.orm_query import (
    orm_get_user,
    orm_get_current_profile_data,
    orm_get_trusted_profiles_list,
    orm_get_user_own_profiles_list,
    orm_get_trusted_users_with_full_info,
    orm_get_global_symptoms,
    orm_get_global_triggers,
    orm_get_triggers_by_profile,
    orm_get_symptoms_by_profile,
)

from database.redis_query import (
    get_redis_cached_current_profile,
    get_redis_cached_login,
    get_redis_cached_profiles_list,
    get_redis_cached_user_id_from_db,
    get_redis_user_timezone,
    get_redis_trusted_persons,
    get_redis_global_triggers_list,
    get_redis_global_symptoms_list,
    get_redis_triggers_list_by_profile,
    get_redis_symptoms_list_by_profile,

    set_redis_trusted_persons,
    set_redis_cached_current_profile,
    set_redis_cached_login,
    set_redis_cached_profiles_list,
    set_redis_cached_user_id_from_db,
    set_redis_trusted_persons,
    set_redis_global_symptoms_list,
    set_redis_global_triggers_list,
    set_redis_symptoms_list_by_profile,
    set_redis_triggers_list_by_profile,
    set_redis_user_timezone,

    delete_redis_cached_current_profile,
    delete_redis_cached_login,
    delete_redis_cached_profiles_list,
    delete_redis_cached_user_id_from_db,
    delete_redis_trusted_persons
)

logger = logging.getLogger(__name__)

# Get operations
async def get_cached_login(session: AsyncSession, user_id: int) -> str:
    login = await get_redis_cached_login(user_id)

    if login:
        logger.debug("Get login from Redis")
        return login

    user = await orm_get_user(session, user_id)
    if not user:
        return None
    login = user.login
    await set_redis_cached_login(user_id, login)
    logger.debug("Get login from DB")

    return login

async def get_cached_user_id_from_db(session: AsyncSession, user_id: int) -> int:
    user_db_id = await get_redis_cached_user_id_from_db(user_id)

    if user_db_id:
        logger.debug("Get user_db_id from Redis")
        return user_db_id

    user = await orm_get_user(session, user_id)
    if not user:
        return None
    user_db_id = user.id
    await set_redis_cached_user_id_from_db(user_id, user_db_id)
    logger.debug("Get user_db_id from DB")

    return user_db_id

async def get_cached_current_profile(session: AsyncSession, user_id: int) -> str:
    current_profile = await get_redis_cached_current_profile(user_id)
    if current_profile:
        logger.debug("Get current profile from Redis")
        return current_profile
    user = await orm_get_user(session, user_id)
    profile = await orm_get_current_profile_data(session, user_id)
    if profile is None:
        return None
    await set_redis_cached_current_profile(user_id, user.current_profile, profile.profile_name)
    logger.debug("Get current profile from DB")

    return f"{user.current_profile}|{profile.profile_name}"

async def get_cached_profiles_list(session: AsyncSession, user_id: int, profile_type: str = "user_own") -> list[str]:
    cached_profiles = await get_redis_cached_profiles_list(user_id, profile_type)
    if cached_profiles:
        logger.debug("Get profiles list from Redis")
        return cached_profiles
    profiles = []
    if profile_type == "trusted":
        profiles = await orm_get_trusted_profiles_list(session, user_id)
    elif profile_type == "user_own":
        profiles = await orm_get_user_own_profiles_list(session, user_id)
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
    user = await orm_get_user(session, user_id)
    if user is None:
        return None
    await set_redis_user_timezone(user_id, user.timezone)
    logger.debug("Get user timezone from DB")
    return user.timezone

async def get_user_local_datetime(session: AsyncSession, user_id: int):
    user_timezone = await get_cached_user_timezone(session, user_id)
    offset = timezone(timedelta(hours=int(user_timezone)))
    return datetime.now(timezone.utc).astimezone(offset)

async def get_cached_trusted_persons_agrigated_data(session: AsyncSession, user_id: int):
    trusted_persons_redis = await get_redis_trusted_persons(user_id)
    if trusted_persons_redis:
        logger.debug("Get trusted persons aggregated data from Redis")
        return trusted_persons_redis

    trusted_persons_db = await orm_get_trusted_users_with_full_info(session, user_id)
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
    symptoms_db = await orm_get_global_symptoms(session)
    await set_redis_global_symptoms_list(user_id, symptoms_db)
    logger.debug("Get global symptoms from DB")
    return symptoms_db

async def get_cached_triggers_list(session: AsyncSession, user_id: int):
    redis_triggers = await get_redis_global_triggers_list(user_id)
    if redis_triggers:
        logger.debug("Get global triggers from Redis")
        return redis_triggers
    triggers_db = await orm_get_global_triggers(session)
    await set_redis_global_triggers_list(user_id, triggers_db)
    logger.debug("Get global triggers from DB")
    return triggers_db

async def get_cached_profile_symptoms_list(session: AsyncSession, user_id: int, profile_id: int):
    redis_profile_symptoms = await get_redis_symptoms_list_by_profile(user_id, profile_id)
    if redis_profile_symptoms:
        logger.debug("Get profile symptoms from Redis")
        return redis_profile_symptoms
    profile_symptoms_db = await orm_get_symptoms_by_profile(session, profile_id)
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
    profile_triggers_db = await orm_get_triggers_by_profile(session, profile_id)
    if profile_triggers_db is None:
        return []
    await set_redis_triggers_list_by_profile(user_id, profile_id, profile_triggers_db)
    logger.debug("Get profile triggers from DB")
    return profile_triggers_db