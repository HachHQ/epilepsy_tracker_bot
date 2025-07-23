import json
import orjson
from database.redis_client import redis

CACHE_TIME = 3600
REQUEST_TIMEOUT = 600

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

async def get_redis_sending_timeout_ten_min(user_id: int):
    cache_key = f"user:timeout_check:{user_id}"
    timeout_check = await redis.get(cache_key)
    return timeout_check.decode('utf-8') if timeout_check else None

async def get_redis_user_timezone(user_id: int):
    cache_key = f"user:timezone:{user_id}"
    timeout_check = await redis.get(cache_key)
    return timeout_check.decode('utf-8') if timeout_check else None

async def get_redis_trusted_persons(user_id: int):
    cache_key = f"user:trusted_persons:{user_id}"
    trusted_persons = await redis.get(cache_key)
    return json.loads(trusted_persons) if trusted_persons else None

async def get_redis_global_triggers_list(user_id: int):
    cache_key = f"user:global_triggers:{user_id}"
    triggers = await redis.get(cache_key)
    return json.loads(triggers.decode('utf-8')) if triggers else None
async def get_redis_global_symptoms_list(user_id: int):
    cache_key = f"user:global_symptoms:{user_id}"
    symptoms = await redis.get(cache_key)
    return symptoms.decode('utf-8') if symptoms else None

async def get_redis_triggers_list_by_profile(user_id: int, profile_id: int):
    cache_key = f"user:profile:triggers:{user_id}:{profile_id}"
    profile_triggers = await redis.get(cache_key)
    return json.loads(profile_triggers.decode('utf-8')) if profile_triggers else None
async def get_redis_symptoms_list_by_profile(user_id: int, profile_id: int):
    cache_key = f"user:profile:symptoms:{user_id}:{profile_id}"
    profile_symptoms = await redis.get(cache_key)
    return profile_symptoms.decode('utf-8') if profile_symptoms else None

# Set operations
async def set_redis_cached_login(user_id: int, login: str):
    await redis.setex(f"user:login:{user_id}", CACHE_TIME, login)

async def set_redis_cached_user_id_from_db(user_id: int, user_db_id: int):
        await redis.setex(f"user:user_db_id:{user_id}", CACHE_TIME, user_db_id)

async def set_redis_cached_current_profile(user_id: int, profile_id: int, profile_name: str):
    profile_key = f"user:current_profile:{user_id}"
    await redis.setex(profile_key, CACHE_TIME, f"{profile_id}|{profile_name}")

async def set_redis_cached_profiles_list(user_id: int, profile_type: str, profiles):
    await redis.setex(f"profiles:{user_id}:{profile_type}", CACHE_TIME, json.dumps(profiles))

async def set_redis_sending_timeout_ten_min(user_id: int, can_send: str):
    await redis.setex(f"user:timeout_check:{user_id}", REQUEST_TIMEOUT, can_send)

async def set_redis_user_timezone(user_id: int, timezone: str):
    await redis.setex(f"user:timezone:{user_id}", CACHE_TIME, timezone)

async def set_redis_trusted_persons(user_id: int, trusted_persons):
    await redis.setex(f"user:trusted_persons:{user_id}", CACHE_TIME, orjson.dumps(trusted_persons))

async def set_redis_global_triggers_list(user_id: int, triggers):
    cache_key = f"user:global_triggers:{user_id}"
    try:
        json_data = json.dumps(triggers)
        await redis.set(cache_key, json_data, CACHE_TIME)
    except Exception as e:
        print(f"Redis save error: {e}")
async def set_redis_global_symptoms_list(user_id: int, symptoms):
    cache_key = f"user:global_symptoms:{user_id}"
    try:
        json_data = json.dumps(symptoms)
        await redis.set(cache_key, json_data, ex=CACHE_TIME)
    except Exception as e:
        print(f"Redis save error: {e}")

async def set_redis_triggers_list_by_profile(user_id: int, profile_id: int, triggers):
    cache_key = f"user:profile:triggers:{user_id}:{profile_id}"
    try:
        print('редис кэш зашли')
        json_data = json.dumps(triggers)
        print('задампали данные')
        await redis.set(cache_key, json_data, CACHE_TIME)
    except Exception as e:
        print(f"Redis save error: {e}")
async def set_redis_symptoms_list_by_profile(user_id: int, profile_id: int, symptoms):
    cache_key = f"user:profile:symptoms:{user_id}:{profile_id}"
    try:
        json_data = json.dumps(symptoms)
        await redis.set(cache_key, json_data, CACHE_TIME)
    except Exception as e:
        print(f"Redis save error: {e}")

# Delete operations
async def delete_redis_cached_login(user_id: int):
    key = f"user:login:{user_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Логин пользователя с ID {user_id} успешно удален из Redis.")
    else:
        print(f"Логин пользователя с ID {user_id} не найден в Redis.")

async def delete_redis_cached_user_id_from_db(user_id: int):
    key = f"user:user_db_id:{user_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"ID from DB пользователя в базе данных пользователя - {user_id} удален из Redis")
    else:
        print(f"ID from DB пользователя в базе данных пользователя - {user_id} не найден в Redis")

async def delete_redis_cached_current_profile(user_id: int):
    key = f"user:current_profile:{user_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Текущий профиль пользователя с ID {user_id} удален из Redis")
    else:
        print(f"Текущий профиль пользователя с ID {user_id} не найден в Redis")

async def delete_redis_cached_profiles_list(user_id: int, profile_type: str):
    key = f"profiles:{user_id}:{profile_type}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Список профилей пользователя - {user_id} удален из Redis")
    else:
        print(f"Список профилей пользователя - {user_id} не найден в Redis")

async def delete_redis_sending_timeout_ten_min(user_id: int):
    key = f"user:timeout_check:{user_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Пользователь найден и теперь может отправить запрос - {user_id}")
    else:
        print(f"Пользователь не найдет, ограничения на отправку нет - {user_id}")

async def delete_redis_trusted_persons(user_id: int):
    key = f"user:trusted_persons:{user_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Доверенные лица пользователя удалены - {user_id}")
    else:
        print(f"Доверенные лица не найдены - {user_id}")

async def delete_redis_global_symptoms(user_id: int):
    key = f"user:global_symptoms:{user_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Глобальные симптомы удалены для юзера - {user_id}")
    else:
        print(f"Глобальные симптомы не найдены для юзера - {user_id}")

async def delete_redis_global_triggers(user_id: int):
    key = f"user:global_triggers:{user_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Глобальные триггеры удалены для юзера - {user_id}")
    else:
        print(f"Глобальные триггеры не найдены для юзера - {user_id}")

async def delete_redis_profile_symptoms_list(user_id: int, profile_id: int):
    key = f"user:profile:symptoms:{user_id}:{profile_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Локальные симптомы профиля удалены для юзера - {user_id} и профиля {profile_id}")
    else:
        print(f"Локальные симптомы профиля не найдены для юзера - {user_id} и профиля {profile_id}")

async def delete_redis_profile_triggers_list(user_id: int, profile_id: int):
    key = f"user:profile:triggers:{user_id}:{profile_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Локальные триггеры профиля удалены для юзера - {user_id} и профиля {profile_id}")
    else:
        print(f"Локальные симптомы профиля не найдены для юзера - {user_id} и профиля {profile_id}")