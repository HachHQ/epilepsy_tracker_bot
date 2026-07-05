import json
import logging
import orjson
from database.redis_client import redis
from services import cache_keys

CACHE_TIME = cache_keys.CACHE_TIME
REQUEST_TIMEOUT = cache_keys.REQUEST_TIMEOUT
logger = logging.getLogger(__name__)


def _decode_json(raw):
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)

# Get operations
async def get_redis_cached_login(user_id: int) -> str:
    login = await redis.get(cache_keys.user_login(user_id))
    return login.decode('utf-8') if login else None

async def get_redis_cached_user_id_from_db(user_id: int) -> int:
    user_db_id = await redis.get(cache_keys.user_db_id(user_id))
    return user_db_id.decode('utf-8') if user_db_id else None

async def get_redis_cached_current_profile(user_id: int) -> str:
    current_profile = await redis.get(cache_keys.current_profile(user_id))
    return current_profile.decode('utf-8') if current_profile else None

async def get_redis_cached_profiles_list(user_id: int, profile_type: str = "user_own") -> list[str]:
    cache_key = cache_keys.profiles_list(user_id, profile_type)
    cached_profiles = await redis.get(cache_key)
    return _decode_json(cached_profiles)

async def get_redis_sending_timeout_ten_min(user_id: int):
    cache_key = cache_keys.sending_timeout(user_id)
    timeout_check = await redis.get(cache_key)
    return timeout_check.decode('utf-8') if timeout_check else None

async def get_redis_user_timezone(user_id: int):
    cache_key = cache_keys.user_timezone(user_id)
    timeout_check = await redis.get(cache_key)
    return timeout_check.decode('utf-8') if timeout_check else None

async def get_redis_trusted_persons(user_id: int):
    cache_key = cache_keys.trusted_persons(user_id)
    trusted_persons = await redis.get(cache_key)
    return _decode_json(trusted_persons)

async def get_redis_global_triggers_list(user_id: int):
    cache_key = cache_keys.global_triggers(user_id)
    triggers = await redis.get(cache_key)
    return _decode_json(triggers)
async def get_redis_global_symptoms_list(user_id: int):
    cache_key = cache_keys.global_symptoms(user_id)
    symptoms = await redis.get(cache_key)
    return _decode_json(symptoms)

async def get_redis_triggers_list_by_profile(user_id: int, profile_id: int):
    cache_key = cache_keys.profile_triggers(user_id, profile_id)
    profile_triggers = await redis.get(cache_key)
    return _decode_json(profile_triggers)
async def get_redis_symptoms_list_by_profile(user_id: int, profile_id: int):
    cache_key = cache_keys.profile_symptoms(user_id, profile_id)
    profile_symptoms = await redis.get(cache_key)
    return _decode_json(profile_symptoms)

# Set operations
async def set_redis_cached_login(user_id: int, login: str):
    await redis.setex(cache_keys.user_login(user_id), CACHE_TIME, login)

async def set_redis_cached_user_id_from_db(user_id: int, user_db_id: int):
        await redis.setex(cache_keys.user_db_id(user_id), CACHE_TIME, user_db_id)

async def set_redis_cached_current_profile(user_id: int, profile_id: int, profile_name: str):
    await redis.setex(cache_keys.current_profile(user_id), CACHE_TIME, f"{profile_id}|{profile_name}")

async def set_redis_cached_profiles_list(user_id: int, profile_type: str, profiles):
    await redis.setex(cache_keys.profiles_list(user_id, profile_type), CACHE_TIME, json.dumps(profiles))

async def set_redis_sending_timeout_ten_min(user_id: int, can_send: str):
    await redis.setex(cache_keys.sending_timeout(user_id), REQUEST_TIMEOUT, can_send)

async def set_redis_user_timezone(user_id: int, timezone: str):
    await redis.setex(cache_keys.user_timezone(user_id), CACHE_TIME, timezone)

async def set_redis_trusted_persons(user_id: int, trusted_persons):
    await redis.setex(cache_keys.trusted_persons(user_id), CACHE_TIME, orjson.dumps(trusted_persons))

async def set_redis_global_triggers_list(user_id: int, triggers):
    cache_key = cache_keys.global_triggers(user_id)
    try:
        json_data = json.dumps(triggers)
        await redis.set(cache_key, json_data, ex=CACHE_TIME)
    except Exception:
        logger.exception("Redis save error for global triggers")
async def set_redis_global_symptoms_list(user_id: int, symptoms):
    cache_key = cache_keys.global_symptoms(user_id)
    try:
        json_data = json.dumps(symptoms)
        await redis.set(cache_key, json_data, ex=CACHE_TIME)
    except Exception:
        logger.exception("Redis save error for global symptoms")

async def set_redis_triggers_list_by_profile(user_id: int, profile_id: int, triggers):
    cache_key = cache_keys.profile_triggers(user_id, profile_id)
    try:
        json_data = json.dumps(triggers)
        await redis.set(cache_key, json_data, ex=CACHE_TIME)
    except Exception:
        logger.exception("Redis save error for profile triggers")
async def set_redis_symptoms_list_by_profile(user_id: int, profile_id: int, symptoms):
    cache_key = cache_keys.profile_symptoms(user_id, profile_id)
    try:
        json_data = json.dumps(symptoms)
        await redis.set(cache_key, json_data, ex=CACHE_TIME)
    except Exception:
        logger.exception("Redis save error for profile symptoms")

# Delete operations
def _log_cache_delete(entity: str, user_id: int, *, deleted: int, profile_id: int | None = None) -> None:
    target = f"{entity} for user_id={user_id}"
    if profile_id is not None:
        target = f"{entity} for user_id={user_id}, profile_id={profile_id}"
    if deleted:
        logger.info("%s deleted from Redis", target)
    else:
        logger.debug("%s not found in Redis", target)


async def delete_redis_cached_login(user_id: int):
    key = cache_keys.user_login(user_id)
    deleted = await redis.delete(key)
    _log_cache_delete("Login cache", user_id, deleted=deleted)

async def delete_redis_cached_user_id_from_db(user_id: int):
    key = cache_keys.user_db_id(user_id)
    deleted = await redis.delete(key)
    _log_cache_delete("User DB id cache", user_id, deleted=deleted)

async def delete_redis_cached_current_profile(user_id: int):
    key = cache_keys.current_profile(user_id)
    deleted = await redis.delete(key)
    _log_cache_delete("Current profile cache", user_id, deleted=deleted)

async def delete_redis_cached_profiles_list(user_id: int, profile_type: str):
    key = cache_keys.profiles_list(user_id, profile_type)
    deleted = await redis.delete(key)
    _log_cache_delete(f"Profiles list ({profile_type})", user_id, deleted=deleted)

async def delete_redis_sending_timeout_ten_min(user_id: int):
    key = cache_keys.sending_timeout(user_id)
    deleted = await redis.delete(key)
    _log_cache_delete("Sending timeout cache", user_id, deleted=deleted)

async def delete_redis_trusted_persons(user_id: int):
    key = cache_keys.trusted_persons(user_id)
    deleted = await redis.delete(key)
    _log_cache_delete("Trusted persons cache", user_id, deleted=deleted)

async def delete_redis_global_symptoms(user_id: int):
    key = cache_keys.global_symptoms(user_id)
    deleted = await redis.delete(key)
    _log_cache_delete("Global symptoms cache", user_id, deleted=deleted)

async def delete_redis_global_triggers(user_id: int):
    key = cache_keys.global_triggers(user_id)
    deleted = await redis.delete(key)
    _log_cache_delete("Global triggers cache", user_id, deleted=deleted)

async def delete_redis_profile_symptoms_list(user_id: int, profile_id: int):
    key = cache_keys.profile_symptoms(user_id, profile_id)
    deleted = await redis.delete(key)
    _log_cache_delete("Profile symptoms cache", user_id, deleted=deleted, profile_id=profile_id)

async def delete_redis_profile_triggers_list(user_id: int, profile_id: int):
    key = cache_keys.profile_triggers(user_id, profile_id)
    deleted = await redis.delete(key)
    _log_cache_delete("Profile triggers cache", user_id, deleted=deleted, profile_id=profile_id)