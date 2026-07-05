from services import cache_keys


def test_user_cache_keys_are_stable() -> None:
    assert cache_keys.user_login(42) == "user:login:42"
    assert cache_keys.user_db_id(42) == "user:user_db_id:42"
    assert cache_keys.current_profile(42) == "user:current_profile:42"


def test_profile_cache_keys_include_type_and_profile_id() -> None:
    assert cache_keys.profiles_list(42, "trusted") == "profiles:42:trusted"
    assert cache_keys.profile_triggers(42, 7) == "user:profile:triggers:42:7"
    assert cache_keys.profile_symptoms(42, 7) == "user:profile:symptoms:42:7"
