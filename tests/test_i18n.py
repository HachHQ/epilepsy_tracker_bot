import pytest

from i18n import (
    DEFAULT_LOCALE,
    get_epilepsy_triggers,
    get_seizure_types,
    resolve_locale,
    set_locale,
    t,
)


def test_resolve_locale_defaults_to_ru() -> None:
    assert resolve_locale(None) == DEFAULT_LOCALE
    assert resolve_locale("en-US") == DEFAULT_LOCALE  # en/ not shipped yet
    assert resolve_locale("de-DE") == DEFAULT_LOCALE


def test_t_returns_russian_string() -> None:
    set_locale("ru")
    assert "Привет" in t("start.welcome")
    assert t("common.yes") == "Да"
    assert t("excel.column_date") == "Дата"


def test_t_supports_format_params() -> None:
    set_locale("ru")
    text = t("account.soft_delete_success", days=180)
    assert "180" in text


def test_domain_lists_loaded() -> None:
    set_locale("ru")
    assert "Стресс" in get_epilepsy_triggers()
    assert get_seizure_types()[5] == "Тонико-клонический"


def test_missing_key_raises_key_error() -> None:
    set_locale("ru")
    with pytest.raises(KeyError):
        t("missing.key")
