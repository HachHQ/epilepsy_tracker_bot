from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.users import get_user_by_chat_id
from handlers_logic.seizure_form.card import (
    duration_step_turn,
    finish_edit,
    review_turn,
    time_step_turn,
)
from handlers_logic.seizure_form.helpers import (
    format_small_date_numbers,
    get_action_btns_flag,
    is_edit_mode,
    parse_callback_data,
    save_seizure_edit,
)
from handlers_logic.seizure_form.screen import FormTurn, answer, edit, turn
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.seizure_kb import (
    get_day_kb,
    get_month_date_kb,
    get_temporary_cancel_submit_kb,
    get_time_ranges_kb,
    get_year_date_kb,
)
from services.notes_formatters import get_minutes_and_seconds
from services.user_timezone import get_local_time_from_offset, get_time_with_minutes_offset
from services.validators import validate_date, validate_non_neg_N_num, validate_time


async def ask_for_a_year(state) -> FormTurn:
    action_btns_flag = await get_action_btns_flag(state)
    return turn(
        answer(
            t("seizure_form.select_year_or_date"),
            reply_markup=get_year_date_kb(4, 0, action_btns=action_btns_flag),
            parse_mode="HTML",
        )
    )


async def handle_short_date(state, db: AsyncSession, chat_id: int, data: str) -> FormTurn:
    parsed = parse_callback_data(data)
    action_btns_flag = await get_action_btns_flag(state)

    if parsed.get("value") in {"two_d_ago", "one_d_ago", "today"}:
        if await is_edit_mode(state):
            await save_seizure_edit(db, chat_id, state, "date", parsed["date"])
            return await finish_edit(
                state, db, answer(t("seizure_form.date_updated", value=parsed["date"])), ack=True
            )
        await state.update_data(date_short=parsed["date"])
        await state.set_state(SeizureForm.hour)
        return await time_step_turn(db, chat_id, edit_message=True)

    await state.update_data(year=parsed["value"])
    await state.set_state(SeizureForm.month)
    return turn(
        edit(
            t("seizure_form.year_selected", year=parsed["value"]),
            reply_markup=get_month_date_kb(action_btns=action_btns_flag),
        ),
        ack=True,
    )


async def handle_month_of_date(state, data: str) -> FormTurn:
    _, month_index, month_name = data.split(":", 2)
    action_btns_flag = await get_action_btns_flag(state)
    await state.update_data(month=format_small_date_numbers(month_index))
    year_month = await state.get_data()
    await state.set_state(SeizureForm.day)
    return turn(
        edit(
            t("seizure_form.month_selected", month_name=month_name),
            reply_markup=get_day_kb(
                int(year_month["year"]),
                int(year_month["month"]),
                action_btns=action_btns_flag,
            ),
        ),
        ack=True,
    )


async def handle_day(state, db: AsyncSession, chat_id: int, data: str) -> FormTurn:
    day_index = data.split(":", 1)[1]
    stored = await state.get_data()
    if await is_edit_mode(state):
        new_date = f"{stored['year']}-{stored['month']}-{day_index}"
        await save_seizure_edit(db, chat_id, state, "date", new_date)
        return await finish_edit(
            state, db, answer(t("seizure_form.date_updated", value=new_date)), ack=True
        )
    await state.update_data(day=format_small_date_numbers(day_index))
    await state.set_state(SeizureForm.hour)
    return await time_step_turn(db, chat_id, edit_message=True)


async def handle_date_by_message(state, db: AsyncSession, chat_id: int, text: str | None) -> FormTurn:
    action_btns_flag = await get_action_btns_flag(state)
    if not validate_date(text or ""):
        return turn(
            answer(
                t("seizure_form.invalid_date"),
                parse_mode="HTML",
                reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
            )
        )
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "date", text)
        return await finish_edit(state, db, answer(t("seizure_form.date_updated", value=text)), ack=False)
    await state.update_data(date_short=text)
    await state.set_state(SeizureForm.hour)
    return await time_step_turn(db, chat_id, edit_message=False)


async def handle_time_of_date_message(state, db: AsyncSession, chat_id: int, text: str | None) -> FormTurn:
    action_btns_flag = await get_action_btns_flag(state)
    if not validate_time(text or ""):
        return turn(
            answer(
                t("seizure_form.invalid_time"),
                reply_markup=get_time_ranges_kb(action_btns=action_btns_flag),
                parse_mode="HTML",
            )
        )
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "time", text)
        return await finish_edit(state, db, answer(t("seizure_form.time_updated", value=text)), ack=False)
    await state.update_data(time_of_day=text)
    await state.set_state(SeizureForm.duration)
    return duration_step_turn(edit_message=False)


async def handle_time_by_btns(state, db: AsyncSession, chat_id: int, data: str) -> FormTurn:
    time_range = data.split(":", 1)[1]
    user = await get_user_by_chat_id(db, chat_id)
    if user is None or not user.timezone:
        return turn(answer(t("seizure_form.restart")), ack=True)
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
        stored = await state.get_data()
        time_value = stored.get("time_of_day")
        await save_seizure_edit(db, chat_id, state, "time", time_value)
        return await finish_edit(
            state, db, answer(t("seizure_form.time_updated", value=time_value)), ack=True
        )
    await state.set_state(SeizureForm.duration)
    return duration_step_turn(edit_message=True)


async def handle_duration_by_cb(state, db: AsyncSession, chat_id: int, data: str) -> FormTurn:
    duration_in_seconds = int(data.split("-", 2)[1])
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "duration", duration_in_seconds)
        return await finish_edit(
            state,
            db,
            answer(t("seizure_form.duration_updated", duration=get_minutes_and_seconds(duration_in_seconds))),
            ack=True,
        )
    await state.update_data(duration=duration_in_seconds)
    return await review_turn(state, db, edit_message=True)


async def handle_duration_by_message(state, db: AsyncSession, chat_id: int, text: str | None) -> FormTurn:
    action_btns_flag = await get_action_btns_flag(state)
    if not validate_non_neg_N_num(text or ""):
        return turn(
            answer(
                t("seizure_form.invalid_duration"),
                parse_mode="HTML",
                reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
            )
        )
    duration_minutes = int(float(text or "0"))
    duration_seconds = duration_minutes * 60
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "duration", duration_seconds)
        return await finish_edit(
            state,
            db,
            answer(t("seizure_form.duration_updated", duration=get_minutes_and_seconds(duration_seconds))),
            ack=False,
        )
    await state.update_data(duration=duration_seconds)
    return await review_turn(state, db, edit_message=False)
