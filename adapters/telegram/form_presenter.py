from aiogram.types import CallbackQuery, Message

from handlers_logic.seizure_form.screen import FormTurn


async def present_form(event: CallbackQuery | Message, form_turn: FormTurn) -> None:
    message = event.message if isinstance(event, CallbackQuery) else event
    if message is None:
        return
    for screen in form_turn.screens:
        if screen.latitude is not None and screen.longitude is not None:
            await message.bot.send_location(
                chat_id=message.chat.id,
                latitude=screen.latitude,
                longitude=screen.longitude,
            )
            continue
        if screen.markup_only:
            await message.edit_reply_markup(reply_markup=screen.reply_markup)
            continue
        kwargs: dict = {}
        if screen.reply_markup is not None:
            kwargs["reply_markup"] = screen.reply_markup
        if screen.parse_mode is not None:
            kwargs["parse_mode"] = screen.parse_mode
        if screen.edit:
            await message.edit_text(screen.text, **kwargs)
        else:
            await message.answer(screen.text, **kwargs)
    if form_turn.ack and isinstance(event, CallbackQuery):
        await event.answer()
