from __future__ import annotations

from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LOCALE = "ru"
SUPPORTED_LOCALES = frozenset({DEFAULT_LOCALE, "en"})

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
_current_locale: ContextVar[str] = ContextVar("locale", default=DEFAULT_LOCALE)


def resolve_locale(language_code: str | None) -> str:
    if not language_code:
        return DEFAULT_LOCALE
    lang = language_code.lower().split("-", 1)[0]
    if lang in SUPPORTED_LOCALES and (_LOCALES_DIR / lang).is_dir():
        return lang
    return DEFAULT_LOCALE


def set_locale(locale: str) -> None:
    _current_locale.set(locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE)


def get_locale() -> str:
    return _current_locale.get()


def _is_catalog_map(value: dict[str, Any]) -> bool:
    return bool(value) and all(str(key).isdigit() for key in value)


def _flatten_mapping(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            if _is_catalog_map(value):
                flat[full_key] = value
            else:
                flat.update(_flatten_mapping(value, full_key))
        else:
            flat[full_key] = value
    return flat


@lru_cache(maxsize=8)
def _load_locale(locale: str) -> dict[str, Any]:
    locale_dir = _LOCALES_DIR / locale
    if not locale_dir.is_dir():
        return {}

    merged: dict[str, Any] = {}
    for path in sorted(locale_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            content = yaml.safe_load(fh) or {}
        if not isinstance(content, dict):
            raise ValueError(f"Locale file must contain a mapping: {path}")
        merged.update(_flatten_mapping(content))
    return merged


def _lookup(key: str, locale: str) -> Any:
    catalog = _load_locale(locale)
    if key in catalog:
        return catalog[key]

    if locale != DEFAULT_LOCALE:
        default_catalog = _load_locale(DEFAULT_LOCALE)
        if key in default_catalog:
            return default_catalog[key]

    raise KeyError(f"Missing translation key '{key}' for locale '{locale}'")


def t(key: str, /, **params: Any) -> str:
    value = _lookup(key, get_locale())
    if not isinstance(value, str):
        raise TypeError(f"Translation key '{key}' is not a string")
    if params:
        return value.format(**params)
    return value


def _lookup_list(key: str) -> list[str]:
    value = _lookup(key, get_locale())
    if not isinstance(value, list):
        raise TypeError(f"Translation key '{key}' is not a list")
    return [str(item) for item in value]


def _lookup_int_map(key: str) -> dict[int, str]:
    value = _lookup(key, get_locale())
    if not isinstance(value, dict):
        raise TypeError(f"Translation key '{key}' is not a mapping")
    return {int(raw_key): str(label) for raw_key, label in value.items()}


def get_month_names() -> list[str]:
    return _lookup_list("domain.month_names")


def get_epilepsy_triggers() -> list[str]:
    return _lookup_list("domain.epilepsy_triggers")


def get_epilepsy_symptoms() -> list[str]:
    return _lookup_list("domain.epilepsy_symptoms")


def get_seizure_types() -> dict[int, str]:
    return _lookup_int_map("domain.seizure_types")
