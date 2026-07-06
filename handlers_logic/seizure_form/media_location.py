from aiogram import Bot
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form.helpers import (
    get_action_btns_flag,
    is_edit_mode,
    save_seizure_edit,
)
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb
from keyboards.seizure_kb import get_final_seizure_btns, get_temporary_cancel_submit_kb
from services.validators import validate_less_than_250


def _extract_video_file_id(message: Message) -> str | None:
    if message.video:
        return message.video.file_id
    if message.video_note:
        return message.video_note.file_id
    if message.document and message.document.mime_type == "video/mp4":
        return message.document.file_id
    return None


async def handle_comment(message: Message, state, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if not validate_less_than_250(message.text):
        await message.answer(
            t("seizure_form.comment_too_long"),
            parse_mode="HTML",
            reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
        )
        return
    if await is_edit_mode(state):
        await save_seizure_edit(db, message.chat.id, state, "comment", message.text)
        await message.answer(t("seizure_form.comment_updated", comment=message.text))
        await state.clear()
        return
    await state.update_data(comment=message.text)
    await state.set_state(SeizureForm.video_tg_id)
    await message.answer(
        t("seizure_form.enter_video"),
        reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
    )


async def handle_video(message: Message, state, db: AsyncSession):
    file_id = _extract_video_file_id(message)
    if await is_edit_mode(state):
        if not file_id:
            await message.answer(t("seizure_form.video_invalid"))
        else:
            await save_seizure_edit(db, message.chat.id, state, "video_tg_id", file_id)
            await message.answer(t("seizure_form.video_saved"))
        await state.clear()
        return
    if not file_id:
        await message.answer(t("seizure_form.video_invalid"))
        return
    await state.update_data(video_tg_id=file_id)
    await message.answer(t("seizure_form.video_saved"), reply_markup=get_temporary_cancel_submit_kb())
    await state.set_state(SeizureForm.location)
    await message.answer(t("seizure_form.location_prompt"), reply_markup=get_geolocation_for_timezone_kb())


async def handle_geolocation(message: Message, state, db: AsyncSession, bot: Bot):
    latitude = message.location.latitude
    longitude = message.location.longitude
    location_coords = f"{latitude}|{longitude}"
    if await is_edit_mode(state):
        await save_seizure_edit(db, message.chat.id, state, "location", location_coords)
        await message.answer(t("seizure_form.geolocation_updated"), reply_markup=ReplyKeyboardRemove())
        await bot.send_location(chat_id=message.chat.id, latitude=latitude, longitude=longitude)
        await state.clear()
        return
    await state.update_data(location=location_coords)
    await message.answer(t("seizure_form.geolocation_saved"), reply_markup=ReplyKeyboardRemove())
    await message.answer(t("seizure_form.finish_prompt"), reply_markup=get_temporary_cancel_submit_kb())


async def handle_location_by_message(message: Message, state, db: AsyncSession):
    if not validate_less_than_250(message.text):
        await message.answer(t("seizure_form.location_too_long"), parse_mode="HTML")
        return
    if await is_edit_mode(state):
        await save_seizure_edit(db, message.chat.id, state, "location", message.text)
        await message.answer(t("seizure_form.location_saved", location=message.text))
        await state.clear()
        return
    await state.update_data(location_by_message=message.text)
    await state.set_state(SeizureForm.count)
    await message.answer(t("seizure_form.location_saved_short"), reply_markup=ReplyKeyboardRemove())
    await message.answer(t("seizure_form.form_complete"), reply_markup=get_final_seizure_btns())
