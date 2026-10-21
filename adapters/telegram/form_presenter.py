from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from adapters.telegram.anchor import live_message
from handlers_logic.seizure_form.screen import FormTurn


async def present_form(event: CallbackQuery | Message, form_turn: FormTurn) -> None:
    message = live_message(event.message) if isinstance(event, CallbackQuery) else event
    if message is None or message.bot is None:
        if form_turn.ack and isinstance(event, CallbackQuery):
            await event.answer()
        return
    bot = message.bot
    for screen in form_turn.screens:
        if screen.latitude is not None and screen.longitude is not None:
            await bot.send_location(
                chat_id=message.chat.id,
                latitude=screen.latitude,
                longitude=screen.longitude,
            )
            continue
        reply_markup = screen.reply_markup
        if screen.markup_only:
            if isinstance(reply_markup, InlineKeyboardMarkup):
                await message.edit_reply_markup(reply_markup=reply_markup)
            continue
        kwargs: dict = {}
        if isinstance(reply_markup, InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove):
            kwargs["reply_markup"] = reply_markup
        if screen.parse_mode is not None:
            kwargs["parse_mode"] = screen.parse_mode
        if screen.text is None:
            continue
        if screen.edit:
            await message.edit_text(screen.text, **kwargs)
        else:
            await message.answer(screen.text, **kwargs)
    if form_turn.ack and isinstance(event, CallbackQuery):
        await event.answer()
