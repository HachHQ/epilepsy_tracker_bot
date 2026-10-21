import asyncio
from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

NOTICE_TTL_SECONDS = 6

_pending: set[asyncio.Task[None]] = set()


def schedule_delete(message: Message, delay: float = NOTICE_TTL_SECONDS) -> None:
    task = asyncio.create_task(_delete_later(message, delay))
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def _delete_later(message: Message, delay: float) -> None:
    await asyncio.sleep(delay)
    with suppress(TelegramBadRequest):
        await message.delete()


async def send_notice(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None = None,
    delay: float = NOTICE_TTL_SECONDS,
) -> Message:
    sent = await message.answer(text, reply_markup=reply_markup)
    schedule_delete(sent, delay)
    return sent
