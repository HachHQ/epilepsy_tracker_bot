from datetime import datetime, timezone

from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_get_user
from handlers_logic.seizure_form.helpers import (
    format_small_date_numbers,
    get_action_btns_flag,
    is_edit_mode,
    parse_callback_data,
    save_seizure_edit,
)
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.seizure_kb import (
    get_day_kb,
    get_duration_kb,
    get_month_date_kb,
    get_temporary_cancel_submit_kb,
    get_time_ranges_kb,
    get_year_date_kb,
)
from services.notes_formatters import get_minutes_and_seconds
from services.user_timezone import get_local_time_from_offset, get_time_with_minutes_offset
from services.validators import validate_date, validate_non_neg_N_num, validate_time


async def ask_for_a_year(message: Message, state):
    action_btns_flag = await get_action_btns_flag(state)
    await message.answer(
        t("seizure_form.select_year_or_date"),
        reply_markup=get_year_date_kb(4, 0, action_btns=action_btns_flag),
        parse_mode="HTML",
    )


async def handle_short_date(callback: CallbackQuery, state, db: AsyncSession):
    parsed = parse_callback_data(callback.data)
    action_btns_flag = await get_action_btns_flag(state)
    data = await state.get_data()

    if parsed.get("value") in {"two_d_ago", "one_d_ago", "today"}:
        if await is_edit_mode(state):
            await save_seizure_edit(db, callback.message.chat.id, state, "date", parsed["date"])
            await callback.message.answer(t("seizure_form.date_updated", value=parsed["date"]))
            await callback.answer()
            await state.clear()
            return
        await state.update_data(date_short=parsed["date"])
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text(
            t("seizure_form.enter_time"),
            reply_markup=get_time_ranges_kb(action_btns=action_btns_flag),
        )
        return

    await state.update_data(year=parsed["value"])
    await state.set_state(SeizureForm.month)
    await callback.message.edit_text(
        t("seizure_form.year_selected", year=parsed["value"]),
        reply_markup=get_month_date_kb(action_btns=action_btns_flag),
    )


async def handle_month_of_date(callback: CallbackQuery, state):
    _, month_index, month_name = callback.data.split(":", 2)
    action_btns_flag = await get_action_btns_flag(state)
    await state.update_data(month=format_small_date_numbers(month_index))
    year_month = await state.get_data()
    await state.set_state(SeizureForm.day)
    await callback.message.edit_text(
        t("seizure_form.month_selected", month_name=month_name),
        reply_markup=get_day_kb(
            int(year_month["year"]),
            int(year_month["month"]),
            action_btns=action_btns_flag,
        ),
    )


async def handle_day(callback: CallbackQuery, state, db: AsyncSession):
    day_index = callback.data.split(":", 1)[1]
    data = await state.get_data()
    action_btns_flag = await get_action_btns_flag(state)
    if await is_edit_mode(state):
        new_date = f"{data['year']}-{data['month']}-{day_index}"
        await save_seizure_edit(db, callback.message.chat.id, state, "date", new_date)
        await callback.message.answer(t("seizure_form.date_updated", value=new_date))
        await callback.answer()
        await state.clear()
        return
    await state.update_data(day=format_small_date_numbers(day_index))
    await state.set_state(SeizureForm.hour)
    await callback.message.edit_text(
        t("seizure_form.enter_time_with_day", day=day_index),
        reply_markup=get_time_ranges_kb(action_btns=action_btns_flag),
    )


async def handle_date_by_message(message: Message, state, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if not validate_date(message.text):
        await message.answer(
            t("seizure_form.invalid_date"),
            parse_mode="HTML",
            reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
        )
        return
    if await is_edit_mode(state):
        await save_seizure_edit(db, message.chat.id, state, "date", message.text)
        await message.answer(t("seizure_form.date_updated", value=message.text))
        await state.clear()
        return
    await state.update_data(date_short=message.text)
    await state.set_state(SeizureForm.hour)
    await message.answer(
        t("seizure_form.enter_time"),
        reply_markup=get_time_ranges_kb(action_btns=action_btns_flag),
    )


async def handle_time_of_date_message(message: Message, state, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if not validate_time(message.text):
        await message.answer(
            t("seizure_form.invalid_time"),
            reply_markup=get_time_ranges_kb(action_btns=action_btns_flag),
            parse_mode="HTML",
        )
        return
    if await is_edit_mode(state):
        await save_seizure_edit(db, message.chat.id, state, "time", message.text)
        await message.answer(t("seizure_form.time_updated", value=message.text))
        await state.clear()
        return
    await state.update_data(time_of_day=message.text)
    await state.set_state(SeizureForm.duration)
    await message.answer(
        t("seizure_form.enter_duration_minutes"),
        reply_markup=get_duration_kb(action_btns=action_btns_flag),
    )


async def handle_time_by_btns(callback: CallbackQuery, state, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    time_range = callback.data.split(":", 1)[1]
    user = await orm_get_user(db, callback.message.chat.id)
    local_user_tz = get_local_time_from_offset(int(user.timezone))
    time_offsets = {
        "now": 0,
        "5m_ago": 5,
        "15m_ago": 15,
        "30m_ago": 30,
        "1h_ago": 60,
        "1p5h_ago": 90,
        "2h_ago": 120,
    }
    if time_range in time_offsets:
        selected_time = get_time_with_minutes_offset(local_user_tz, time_offsets[time_range])
        await state.update_data(time_of_day=str(selected_time.time().isoformat(timespec="minutes")))
    if await is_edit_mode(state):
        data = await state.get_data()
        time_value = data.get("time_of_day")
        await save_seizure_edit(db, callback.message.chat.id, state, "time", time_value)
        await callback.message.answer(t("seizure_form.time_updated", value=time_value))
        await callback.answer()
        await state.clear()
        return
    await state.set_state(SeizureForm.duration)
    await callback.message.edit_text(
        t("seizure_form.enter_duration_minutes"),
        reply_markup=get_duration_kb(action_btns=action_btns_flag),
    )
    await callback.answer()


async def handle_duration_by_cb(callback: CallbackQuery, state, db: AsyncSession):
    duration_in_seconds = int(callback.data.split("-", 2)[1])
    action_btns_flag = await get_action_btns_flag(state)
    if await is_edit_mode(state):
        await save_seizure_edit(db, callback.message.chat.id, state, "duration", duration_in_seconds)
        await callback.message.answer(
            t("seizure_form.duration_updated", duration=get_minutes_and_seconds(duration_in_seconds))
        )
        await callback.answer()
        await state.clear()
        return
    await state.update_data(duration=duration_in_seconds)
    await callback.message.edit_text(
        t("seizure_form.select_count"),
        reply_markup=get_count_of_seizures_kb(action_btns_flag),
    )
    await state.set_state(SeizureForm.count)
    await callback.answer()


async def handle_duration_by_message(message: Message, state, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if not validate_non_neg_N_num(message.text):
        await message.answer(
            t("seizure_form.invalid_duration"),
            parse_mode="HTML",
            reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
        )
        return
    duration_minutes = int(float(message.text))
    duration_seconds = duration_minutes * 60
    if await is_edit_mode(state):
        await save_seizure_edit(db, message.chat.id, state, "duration", duration_seconds)
        await message.answer(
            t("seizure_form.duration_updated", duration=get_minutes_and_seconds(duration_seconds))
        )
        await state.clear()
        return
    await state.update_data(duration=duration_seconds)
    await state.set_state(SeizureForm.count)
    await message.answer(
        t("seizure_form.select_count"),
        reply_markup=get_count_of_seizures_kb(action_btns=action_btns_flag),
    )
