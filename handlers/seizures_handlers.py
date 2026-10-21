from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.anchor import live_message
from adapters.telegram.form_presenter import present_form
from filters.correct_commands import ProfileIsSetCb, ProfileIsSetMsg
from handlers_logic.access_reply import deny_read_only
from handlers_logic.seizure_form import (
    handle_comment,
    handle_count_by_message,
    handle_count_of_seizures,
    handle_date_by_message,
    handle_day,
    handle_duration_by_cb,
    handle_duration_by_message,
    handle_geolocation,
    handle_location_by_message,
    handle_month_of_date,
    handle_save_symptoms,
    handle_save_toggled_triggers,
    handle_seizre_right_now,
    handle_severity,
    handle_short_date,
    handle_skip_step,
    handle_stop_tracking_duration,
    handle_symptoms_by_message,
    handle_symptoms_page,
    handle_time_by_btns,
    handle_time_of_date_message,
    handle_toggle_symptom,
    handle_toggle_trigger,
    handle_triggers_by_message,
    handle_triggers_page,
    handle_type_of_seizure_page,
    handle_type_of_seizure_save,
    handle_video,
    start_seizure_field_edit,
)
from handlers_logic.seizure_form.card import (
    handle_back,
    open_count_picker,
    open_passed_form,
    open_type_picker,
    saved_from_preview,
)
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.seizure_kb import get_enrich_kb, get_seizure_timing
from services.profile_ref import ProfileRef
from services.redis_cache_data import get_cached_login
from use_cases.medications import medication_text_on
from use_cases.seizures import create_seizure_from_state

seizures_router = Router()


@seizures_router.callback_query(F.data == "skip_step")
async def process_skip_step(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    profile_id = None if current_profile is None else current_profile.id
    await present_form(
        callback, await handle_skip_step(state, db, message.chat.id, profile_id)
    )


@seizures_router.callback_query(F.data == "fix_seizure")
async def process_right_now_or_passed(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    await message.edit_text(
        t("seizure_form.fix_seizure_prompt"),
        reply_markup=get_seizure_timing(),
    )


@seizures_router.callback_query((F.data == "check_input_seizure_data") | (F.data == "seizure_save"))
async def process_save_and_display_seizure_data(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    current_profile: ProfileRef | None,
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    seizure_data = await state.get_data()
    login = await get_cached_login(db, message.chat.id)
    if not seizure_data:
        await message.answer(t("seizure.restart_form"))
        await callback.answer()
        return
    if current_profile is None or login is None:
        await message.answer(t("seizure.select_profile_first"))
        await callback.answer()
        return
    if await deny_read_only(callback, current_profile):
        return
    preview = await create_seizure_from_state(
        db,
        user_id=message.chat.id,
        profile=current_profile,
        creator_login=login,
        state_data=seizure_data,
    )
    if preview is None:
        await callback.answer()
        return
    medication = await medication_text_on(db, current_profile.id, preview.date)
    await message.edit_text(
        saved_from_preview(preview, medication),
        reply_markup=get_enrich_kb(preview.seizure_id),
    )
    await callback.answer()
    await state.clear()


@seizures_router.callback_query(F.data == "seizure_right_now", ProfileIsSetCb())
async def process_seizre_right_now(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    if await deny_read_only(callback, current_profile):
        return
    profile_id = None if current_profile is None else current_profile.id
    await present_form(
        callback,
        await handle_seizre_right_now(
            state, db, message.chat.id, profile_id, edit_message=True
        ),
    )


@seizures_router.message(Command("now"), ProfileIsSetMsg())
async def process_seizure_now(
    message: Message, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    if await deny_read_only(message, current_profile):
        return
    profile_id = None if current_profile is None else current_profile.id
    await present_form(
        message,
        await handle_seizre_right_now(state, db, message.chat.id, profile_id, edit_message=False),
    )


@seizures_router.callback_query(F.data == "stop_track_duration")
async def process_stop_tracking_duration(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await present_form(callback, await handle_stop_tracking_duration(state, db))


@seizures_router.callback_query(F.data.startswith("seizure_passed"), ProfileIsSetCb())
async def start_fix_seizure(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    if await deny_read_only(callback, current_profile):
        return
    profile_id = None if current_profile is None else current_profile.id
    await present_form(
        callback,
        await open_passed_form(state, db, message.chat.id, profile_id),
    )


@seizures_router.callback_query(F.data == "seizure_back")
async def process_seizure_back(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    await present_form(callback, await handle_back(state, db, message.chat.id))


@seizures_router.callback_query(F.data == "seizure_pick_type", StateFilter(SeizureForm.review))
async def process_pick_type(callback: CallbackQuery, state: FSMContext):
    await present_form(callback, await open_type_picker(state))


@seizures_router.callback_query(F.data == "seizure_pick_count", StateFilter(SeizureForm.review))
async def process_pick_count(callback: CallbackQuery, state: FSMContext):
    await present_form(callback, await open_count_picker(state))


@seizures_router.callback_query(F.data.startswith("enrich:"))
async def process_enrich(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    _, action, seizure_id = payload.split(":", 2)
    if current_profile is None:
        await callback.answer()
        return
    if await deny_read_only(callback, current_profile):
        return
    form_turn = await start_seizure_field_edit(
        state,
        db,
        action=action,
        seizure_id=int(seizure_id),
        profile_id=current_profile.id,
        chat_id=message.chat.id,
    )
    await state.update_data(enrich=True)
    await present_form(callback, form_turn)


@seizures_router.callback_query(F.data.startswith("year"), StateFilter(SeizureForm.year))
async def process_date_short(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback, await handle_short_date(state, db, message.chat.id, payload)
    )


@seizures_router.message(StateFilter(SeizureForm.year))
async def process_year_by_message(message: Message, state: FSMContext, db: AsyncSession):
    await present_form(message, await handle_date_by_message(state, db, message.chat.id, message.text))


@seizures_router.callback_query(F.data.startswith("month"), StateFilter(SeizureForm.month))
async def process_month_of_date(callback: CallbackQuery, state: FSMContext):
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(callback, await handle_month_of_date(state, payload))


@seizures_router.callback_query(F.data.startswith("day"), StateFilter(SeizureForm.day))
async def process_day_of_date(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(callback, await handle_day(state, db, message.chat.id, payload))


@seizures_router.message(StateFilter(SeizureForm.hour))
async def process_time_of_date_message(message: Message, state: FSMContext, db: AsyncSession):
    await present_form(
        message, await handle_time_of_date_message(state, db, message.chat.id, message.text)
    )


@seizures_router.callback_query(F.data.startswith("time_range"), StateFilter(SeizureForm.hour))
async def process_time_by_btns(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback, await handle_time_by_btns(state, db, message.chat.id, payload)
    )


@seizures_router.callback_query(F.data.startswith("count_of_seizures"), StateFilter(SeizureForm.count))
async def process_count_of_seizures(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback, await handle_count_of_seizures(state, db, message.chat.id, payload)
    )


@seizures_router.callback_query(F.data.startswith("seizure_type_page"), StateFilter(SeizureForm.type_of_seizure))
async def process_type_of_seizure_page(callback: CallbackQuery, state: FSMContext):
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    stored = await state.get_data()
    await present_form(
        callback,
        await handle_type_of_seizure_page(payload, back=bool(stored.get("return_to_review"))),
    )


@seizures_router.callback_query(F.data.startswith("seizure_type"), StateFilter(SeizureForm.type_of_seizure))
async def process_type_of_seizure_save(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback,
        await handle_type_of_seizure_save(
            state,
            db,
            message.chat.id,
            None if current_profile is None else current_profile.id,
            payload,
        ),
    )


@seizures_router.message(StateFilter(SeizureForm.count))
async def process_count_message(message: Message, state: FSMContext, db: AsyncSession):
    await present_form(message, await handle_count_by_message(state, db, message.chat.id, message.text))


@seizures_router.callback_query(F.data.startswith("toggle"), StateFilter(SeizureForm.triggers))
async def process_toggle_trigger(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback,
        await handle_toggle_trigger(
            state,
            db,
            message.chat.id,
            None if current_profile is None else current_profile.id,
            payload,
        ),
    )


@seizures_router.callback_query(F.data.startswith("page"), StateFilter(SeizureForm.triggers))
async def process_triggers_page(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback,
        await handle_triggers_page(
            state,
            db,
            message.chat.id,
            None if current_profile is None else current_profile.id,
            payload,
        ),
    )


@seizures_router.callback_query(F.data.startswith("done"), StateFilter(SeizureForm.triggers))
async def process_save_toggled_triggers(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    await present_form(
        callback, await handle_save_toggled_triggers(state, db, message.chat.id)
    )


@seizures_router.message(StateFilter(SeizureForm.triggers))
async def process_triggers_message(message: Message, state: FSMContext, db: AsyncSession):
    await present_form(
        message, await handle_triggers_by_message(state, db, message.chat.id, message.text)
    )


@seizures_router.callback_query(F.data.startswith("toggle"), StateFilter(SeizureForm.symptoms))
async def process_toggle_symptom(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback,
        await handle_toggle_symptom(
            state,
            db,
            message.chat.id,
            None if current_profile is None else current_profile.id,
            payload,
        ),
    )


@seizures_router.callback_query(F.data.startswith("page"), StateFilter(SeizureForm.symptoms))
async def process_symptoms_page(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback,
        await handle_symptoms_page(
            state,
            db,
            message.chat.id,
            None if current_profile is None else current_profile.id,
            payload,
        ),
    )


@seizures_router.callback_query(F.data.startswith("done"), StateFilter(SeizureForm.symptoms))
async def process_save_symptoms(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    await present_form(callback, await handle_save_symptoms(state, db, message.chat.id))


@seizures_router.message(StateFilter(SeizureForm.symptoms))
async def process_symptoms_message(message: Message, state: FSMContext, db: AsyncSession):
    await present_form(
        message, await handle_symptoms_by_message(state, db, message.chat.id, message.text)
    )


@seizures_router.callback_query(F.data.startswith("saverity"), StateFilter(SeizureForm.severity))
async def process_severity_message(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback, await handle_severity(state, db, message.chat.id, payload)
    )


@seizures_router.callback_query(F.data.startswith("seizure_duration"), StateFilter(SeizureForm.duration))
async def process_duration_cb(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await present_form(
        callback, await handle_duration_by_cb(state, db, message.chat.id, payload)
    )


@seizures_router.message(StateFilter(SeizureForm.duration))
async def process_duration_message(message: Message, state: FSMContext, db: AsyncSession):
    await present_form(
        message, await handle_duration_by_message(state, db, message.chat.id, message.text)
    )


@seizures_router.message(StateFilter(SeizureForm.comment))
async def process_comment_message(message: Message, state: FSMContext, db: AsyncSession):
    await present_form(message, await handle_comment(state, db, message.chat.id, message.text))


@seizures_router.message((F.video) | (F.document) | (F.video_note), StateFilter(SeizureForm.video_tg_id))
async def process_video(message: Message, state: FSMContext, db: AsyncSession):
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.video_note:
        file_id = message.video_note.file_id
    elif message.document and message.document.mime_type == "video/mp4":
        file_id = message.document.file_id
    await present_form(message, await handle_video(state, db, message.chat.id, file_id))


@seizures_router.message(F.location, StateFilter(SeizureForm.location))
async def process_location_of_seizure(message: Message, state: FSMContext, db: AsyncSession):
    if message.location is None:
        return
    await present_form(
        message,
        await handle_geolocation(
            state, db, message.chat.id, message.location.latitude, message.location.longitude
        ),
    )


@seizures_router.message(StateFilter(SeizureForm.location))
async def process_location_by_message(message: Message, state: FSMContext, db: AsyncSession):
    await present_form(
        message, await handle_location_by_message(state, db, message.chat.id, message.text)
    )
