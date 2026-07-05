from types import SimpleNamespace
from unittest.mock import patch

from config_data.config import get_config, load_config


def test_get_config_uses_cached_instance() -> None:
    get_config.cache_clear()
    config = SimpleNamespace(app="test-config")

    with patch("config_data.config.load_config", return_value=config) as loader:
        first = get_config()
        second = get_config()

    assert first is second
    loader.assert_called_once_with(".env", strict=True)
    get_config.cache_clear()


def test_get_config_strict_false_is_separate_cache_entry() -> None:
    get_config.cache_clear()
    strict_config = SimpleNamespace(mode="strict")
    dev_config = SimpleNamespace(mode="dev")

    with patch(
        "config_data.config.load_config",
        side_effect=[strict_config, dev_config],
    ) as loader:
        assert get_config() is strict_config
        assert get_config(strict=False) is dev_config

    assert loader.call_count == 2
    get_config.cache_clear()
