from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import MessageEntityType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, TelegramObject

from config_data.command_cleanup import DELETE_AFTER_COMMANDS


def _extract_command_name(message: Message) -> str | None:
    if not message.text or not message.entities:
        return None
    for entity in message.entities:
        if entity.type != MessageEntityType.BOT_COMMAND:
            continue
        command = message.text[entity.offset : entity.offset + entity.length]
        return command.lstrip("/").split("@", 1)[0].lower()
    return None


class DeleteCommandMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)
        if not isinstance(event, Message):
            return result

        command_name = _extract_command_name(event)
        if command_name is None or command_name not in DELETE_AFTER_COMMANDS:
            return result

        with suppress(TelegramBadRequest):
            await event.delete()

        return result
