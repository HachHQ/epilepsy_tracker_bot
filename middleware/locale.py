from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from i18n import resolve_locale, set_locale


def _extract_language_code(event: TelegramObject) -> str | None:
    user = None
    if isinstance(event, Message):
        user = event.from_user
    elif isinstance(event, CallbackQuery):
        user = event.from_user
    if user is None:
        return None
    return user.language_code


class LocaleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        locale = resolve_locale(_extract_language_code(event))
        set_locale(locale)
        data["locale"] = locale
        return await handler(event, data)
