from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_get_user,
    orm_get_current_profile_data,
    orm_get_trusted_profiles_list,
    orm_get_user_own_profiles_list,
)
from database.redis_query import (
    get_redis_cached_current_profile,
    get_redis_cached_login,
    get_redis_cached_profiles_list,
    get_redis_cached_user_id_from_db,

    set_redis_cached_current_profile,
    set_redis_cached_login,
    set_redis_cached_profiles_list,
    set_redis_cached_user_id_from_db,

    delete_redis_cached_current_profile,
    delete_redis_cached_login,
    delete_redis_cached_profiles_list,
    delete_redis_cached_user_id_from_db
)

# Get operations
async def get_cached_login(session: AsyncSession, user_id: int) -> str:
    login = await get_redis_cached_login(user_id)

    if login:
        print('get login from redis')
        return login

    user = await orm_get_user(session, user_id)
    if not user:
        return None
    login = user.login
    await set_redis_cached_login(user_id, login)
    print("from db")

    return login

async def get_cached_user_id_from_db(session: AsyncSession, user_id: int) -> int:
    user_db_id = await get_redis_cached_user_id_from_db(user_id)

    if user_db_id:
        print("get user_db_id from redis")
        return user_db_id

    user = await orm_get_user(session, user_id)
    if not user:
        return None
    user_db_id = user.id
    await set_redis_cached_user_id_from_db(user_id, user_db_id)
    print("from db")

    return user_db_id

async def get_cached_current_profile(session: AsyncSession, user_id: int) -> str:
    current_profile = await get_redis_cached_current_profile(user_id)
    if current_profile:
        print("get current_profile from redis")
        return current_profile
    user = await orm_get_user(session, user_id)
    profile = await orm_get_current_profile_data(session, user_id)
    if profile is None:
        return None
    await set_redis_cached_current_profile(user_id, user.current_profile, profile.profile_name)
    print("get current profile from db")

    return f"{user.current_profile}|{profile.profile_name}"

async def get_cached_profiles_list(session: AsyncSession, user_id: int, profile_type: str = "user_own") -> list[str]:
    cached_profiles = await get_redis_cached_profiles_list(user_id, profile_type)
    if cached_profiles:
        print("get cached profiles list from redis")
        return cached_profiles
    profiles = []
    if profile_type == "trusted":
        profiles = await orm_get_trusted_profiles_list(session, user_id)
        print(f"DB {profiles}")
    elif profile_type == "user_own":
        profiles = await orm_get_user_own_profiles_list(session, user_id)
        print(f"DB {profiles}")

    if not profiles:
        return None
    print("get profiles list from db")
    await set_redis_cached_profiles_list(user_id=user_id, profile_type=profile_type, profiles=profiles)
    return profiles
