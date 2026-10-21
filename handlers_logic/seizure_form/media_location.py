from aiogram.types import ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form.card import finish_edit
from handlers_logic.seizure_form.helpers import (
    get_action_btns_flag,
    is_edit_mode,
    save_seizure_edit,
)
from handlers_logic.seizure_form.screen import FormTurn, answer, turn
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb
from keyboards.seizure_kb import get_final_seizure_btns, get_temporary_cancel_submit_kb
from services.validators import validate_less_than_250


async def handle_comment(state, db: AsyncSession, chat_id: int, text: str | None) -> FormTurn:
    action_btns_flag = await get_action_btns_flag(state)
    if not validate_less_than_250(text or ""):
        return turn(
            answer(
                t("seizure_form.comment_too_long"),
                parse_mode="HTML",
                reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
            )
        )
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "comment", text)
        return await finish_edit(state, db, answer(t("seizure_form.comment_updated", comment=text)), ack=False)
    await state.update_data(comment=text)
    await state.set_state(SeizureForm.video_tg_id)
    return turn(
        answer(
            t("seizure_form.enter_video"),
            reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
        )
    )


async def handle_video(state, db: AsyncSession, chat_id: int, file_id: str | None) -> FormTurn:
    if await is_edit_mode(state):
        if not file_id:
            return turn(answer(t("seizure_form.video_invalid")))
        await save_seizure_edit(db, chat_id, state, "video_tg_id", file_id)
        return await finish_edit(state, db, answer(t("seizure_form.video_saved")), ack=False)
    if not file_id:
        return turn(answer(t("seizure_form.video_invalid")))
    await state.update_data(video_tg_id=file_id)
    await state.set_state(SeizureForm.location)
    return turn(
        answer(t("seizure_form.video_saved"), reply_markup=get_temporary_cancel_submit_kb()),
        answer(t("seizure_form.location_prompt"), reply_markup=get_geolocation_for_timezone_kb()),
    )


async def handle_geolocation(
    state, db: AsyncSession, chat_id: int, latitude: float, longitude: float
) -> FormTurn:
    location_coords = f"{latitude}|{longitude}"
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "location", location_coords)
        return await finish_edit(
            state,
            db,
            answer(t("seizure_form.geolocation_updated"), reply_markup=ReplyKeyboardRemove()),
            ack=False,
        )
    await state.update_data(location=location_coords)
    return turn(
        answer(t("seizure_form.geolocation_saved"), reply_markup=ReplyKeyboardRemove()),
        answer(t("seizure_form.finish_prompt"), reply_markup=get_temporary_cancel_submit_kb()),
    )


async def handle_location_by_message(state, db: AsyncSession, chat_id: int, text: str | None) -> FormTurn:
    if not validate_less_than_250(text or ""):
        return turn(answer(t("seizure_form.location_too_long"), parse_mode="HTML"))
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "location", text)
        return await finish_edit(
            state, db, answer(t("seizure_form.location_saved", location=text)), ack=False
        )
    await state.update_data(location_by_message=text)
    await state.set_state(SeizureForm.count)
    return turn(
        answer(t("seizure_form.location_saved_short"), reply_markup=ReplyKeyboardRemove()),
        answer(t("seizure_form.form_complete"), reply_markup=get_final_seizure_btns()),
    )
