import os

from aiogram import Bot
from aiogram.types import FSInputFile, Message

from database.models import Seizure
from services.notes_formatters import SeizureDisplayPayload, build_seizure_display, get_minutes_and_seconds, parse_location_coords
from use_cases.seizures import SeizurePreview


async def show_seizure_preview(bot: Bot, message: Message, preview: SeizurePreview) -> None:
    await show_seizure_note(
        bot,
        message,
        seizure_id=preview.seizure_id,
        current_profile=preview.profile_name,
        date=preview.date,
        time=preview.time,
        count=preview.count,
        triggers=preview.triggers,
        severity=preview.severity,
        duration=preview.duration,
        comment=preview.comment,
        symptoms=preview.symptoms,
        type_of_seizure=preview.type_of_seizure,
        video_tg_id=preview.video_tg_id,
        location=preview.location,
    )


async def show_seizure_from_model(
    bot: Bot,
    message: Message,
    seizure: Seizure,
    profile_name: str,
    *,
    edit_mode: bool = False,
) -> None:
    await show_seizure_note(
        bot,
        message,
        seizure_id=seizure.id,
        current_profile=profile_name,
        date=seizure.date,
        time=seizure.time,
        count=seizure.count,
        triggers=seizure.triggers,
        severity=seizure.severity,
        duration=get_minutes_and_seconds(seizure.duration),
        comment=seizure.comment,
        symptoms=seizure.symptoms,
        video_tg_id=seizure.video_tg_id,
        location=seizure.location,
        type_of_seizure=seizure.type_of_seizure,
        edit_mode=edit_mode,
    )


async def deliver_seizure_display(
    bot: Bot,
    message: Message,
    payload: SeizureDisplayPayload,
    *,
    edit_mode: bool = False,
) -> None:
    await message.answer(payload.text, parse_mode="HTML")
    if edit_mode:
        return
    if payload.video_tg_id:
        await bot.send_video(chat_id=message.chat.id, video=payload.video_tg_id)
    coords = parse_location_coords(payload.location)
    if coords:
        await bot.send_location(message.chat.id, coords[0], coords[1])


async def show_seizure_note(bot: Bot, message: Message, **fields) -> None:
    edit_mode = fields.pop("edit_mode", False)
    payload = build_seizure_display(**fields, edit_mode=edit_mode)
    await deliver_seizure_display(bot, message, payload, edit_mode=edit_mode)


async def send_chart_photo(message: Message, image_path: str, caption: str) -> None:
    try:
        await message.answer_photo(photo=FSInputFile(image_path), caption=caption)
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


async def send_document_file(
    bot: Bot,
    chat_id: int,
    file_path: str,
    *,
    caption: str | None = None,
    remove_after: bool = True,
) -> None:
    try:
        await bot.send_document(chat_id=chat_id, document=FSInputFile(file_path), caption=caption)
    finally:
        if remove_after and os.path.exists(file_path):
            os.remove(file_path)
