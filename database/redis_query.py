import json
from database.redis_client import redis

# Get operations
async def get_redis_cached_login(user_id: int) -> str:
    login = await redis.get(f"user:login:{user_id}")
    return login.decode('utf-8') if login else None

async def get_redis_cached_user_id_from_db(user_id: int) -> int:
    user_db_id = await redis.get(f"user:user_db_id:{user_id}")
    return user_db_id.decode('utf-8') if user_db_id else None

async def get_redis_cached_current_profile(user_id: int) -> str:
    profile_key = f"user:current_profile:{user_id}"
    current_profile = await redis.get(profile_key)
    return current_profile.decode('utf-8') if current_profile else None

async def get_redis_cached_profiles_list(user_id: int, profile_type: str = "user_own") -> list[str]:
    cache_key = f"profiles:{user_id}:{profile_type}"
    cached_profiles = await redis.get(cache_key)
    return json.loads(cached_profiles.decode('utf-8')) if cached_profiles else None


# Set operations
async def set_redis_cached_login(user_id: int, login: str):
    await redis.setex(f"user:login:{user_id}", 3600, login)

async def set_redis_cached_user_id_from_db(user_id: int, user_db_id: int):
        await redis.setex(f"user:user_db_id:{user_id}", 3600, user_db_id)

async def set_redis_cached_current_profile(user_id: int, profile_id: int, profile_name: str):
    profile_key = f"user:current_profile:{user_id}"
    await redis.setex(profile_key, 3600, f"{profile_id}|{profile_name}")

async def set_redis_cached_profiles_list(user_id: int, profile_type: str, profiles):
    await redis.setex(f"profiles:{user_id}:{profile_type}", 3600, json.dumps(profiles))

# Delete operations
async def delete_redis_cached_login(user_id: int):
    login_key = f"user:login:{user_id}"
    deleted = await redis.delete(login_key)
    if deleted:
        print(f"Логин пользователя с ID {user_id} успешно удален из Redis.")
    else:
        print(f"Логин пользователя с ID {user_id} не найден в Redis.")

async def delete_redis_cached_user_id_from_db(user_id: int):
    user_id_db_key = f"user:user_db_id:{user_id}"
    deleted = await redis.delete(user_id_db_key)
    if deleted:
        print(f"ID from DB пользователя в базе данных пользователя - {user_id} удален из Redis")
    else:
        print(f"ID from DB пользователя в базе данных пользователя - {user_id} не найден в Redis")

async def delete_redis_cached_current_profile(user_id: int):
    profile_key = f"user:current_profile:{user_id}"
    deleted = await redis.delete(profile_key)
    if deleted:
        print(f"Текущий профиль пользователя с ID {user_id} удален из Redis")
    else:
        print(f"Текущий профиль пользователя с ID {user_id} не найден в Redis")

async def delete_redis_cached_profiles_list(user_id: int):
    profile_key = f"user:current_profile:{user_id}"
    deleted = await redis.delete(profile_key)
    if deleted:
        print(f"Список профилей пользователя - {user_id} удален из Redis")
    else:
        print(f"Список профилей пользователя - {user_id} не найден в Redis")