from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InaccessibleMessage,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

ANCHOR_MESSAGE_ID = "anchor_message_id"


def live_message(message: Message | InaccessibleMessage | None) -> Message | None:
    if message is None or isinstance(message, InaccessibleMessage):
        return None
    return message


async def drop_anchor(bot: Bot | None, chat_id: int, state: FSMContext) -> None:
    if bot is None:
        return
    anchor_id = (await state.get_data()).get(ANCHOR_MESSAGE_ID)
    if not isinstance(anchor_id, int):
        return
    with suppress(TelegramBadRequest):
        await bot.delete_message(chat_id=chat_id, message_id=anchor_id)


async def send_anchor(
    message: Message,
    state: FSMContext,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None = None,
    parse_mode: str | None = None,
) -> Message:
    """Replace the previous prompt so the current step stays at the bottom of the chat."""
    await drop_anchor(message.bot, message.chat.id, state)
    sent = await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    await state.update_data({ANCHOR_MESSAGE_ID: sent.message_id})
    return sent
