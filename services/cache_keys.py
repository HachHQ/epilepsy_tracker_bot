CACHE_TIME = 3600
REQUEST_TIMEOUT = 600


def user_login(user_id: int) -> str:
    return f"user:login:{user_id}"


def user_db_id(user_id: int) -> str:
    return f"user:user_db_id:{user_id}"


def current_profile(user_id: int) -> str:
    return f"user:current_profile:{user_id}"


def profiles_list(user_id: int, profile_type: str) -> str:
    return f"profiles:{user_id}:{profile_type}"


def sending_timeout(user_id: int) -> str:
    return f"user:timeout_check:{user_id}"


def user_timezone(user_id: int) -> str:
    return f"user:timezone:{user_id}"


def trusted_persons(user_id: int) -> str:
    return f"user:trusted_persons:{user_id}"


def global_triggers(user_id: int) -> str:
    return f"user:global_triggers:{user_id}"


def global_symptoms(user_id: int) -> str:
    return f"user:global_symptoms:{user_id}"


def profile_triggers(user_id: int, profile_id: int) -> str:
    return f"user:profile:triggers:{user_id}:{profile_id}"


def profile_symptoms(user_id: int, profile_id: int) -> str:
    return f"user:profile:symptoms:{user_id}:{profile_id}"
