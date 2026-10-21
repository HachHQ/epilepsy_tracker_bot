from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import ChatType, MessageEntityType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, TelegramObject, Update


def _is_command(message: Message) -> bool:
    text = message.text or message.caption
    entities = message.entities if message.text else message.caption_entities
    if not text or not entities:
        return False
    return any(
        entity.type == MessageEntityType.BOT_COMMAND and entity.offset == 0
        for entity in entities
    )


def _incoming_message(event: TelegramObject) -> Message | None:
    if isinstance(event, Message):
        return event
    if isinstance(event, Update):
        return event.message
    return None


def should_delete_plain_message(message: Message, data: dict[str, Any]) -> bool:
    """Private-chat messages outside an active form, except bot commands."""
    if message.chat.type != ChatType.PRIVATE:
        return False
    if "raw_state" not in data or data["raw_state"] is not None:
        return False
    return not _is_command(message)


class DeletePlainMessageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)
        message = _incoming_message(event)
        if message is not None and should_delete_plain_message(message, data):
            with suppress(TelegramBadRequest):
                await message.delete()
        return result
