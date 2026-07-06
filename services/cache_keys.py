"""Redis cache key builders and invalidation contract."""

CACHE_TIME = 3600
REQUEST_TIMEOUT = 600

# Logical cache groups invalidated by domain events (see services/cache_invalidation.py).
INVALIDATION_CONTRACT: dict[str, tuple[str, ...]] = {
    "seizure.create": (
        "profile_triggers",
        "profile_symptoms",
        "global_triggers",
        "global_symptoms",
    ),
    "seizure.update.triggers": ("profile_triggers", "global_triggers"),
    "seizure.update.symptoms": ("profile_symptoms", "global_symptoms"),
    "profile.delete": ("current_profile", "profiles_list:user_own"),
    "trusted_person.mutate": ("trusted_persons", "profiles_list:trusted"),
    "user.account.delete": ("login", "profiles_list", "current_profile", "trusted_persons"),
}


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
