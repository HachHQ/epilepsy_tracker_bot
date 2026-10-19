from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form.card import apply_last_defaults, review_turn, user_local_now
from handlers_logic.seizure_form.screen import FormTurn, answer, edit, turn
from i18n import t
from keyboards.seizure_kb import get_stop_duration_kb


async def handle_seizre_right_now(
    state,
    db: AsyncSession,
    chat_id: int,
    profile_id: int | None,
    *,
    edit_message: bool,
) -> FormTurn:
    await state.clear()
    local_user_tz = await user_local_now(db, chat_id)
    if local_user_tz is None:
        return turn(answer(t("seizure_form.restart")), ack=edit_message)
    await apply_last_defaults(db, profile_id, state)
    await state.update_data(
        phase="live",
        profile_id=profile_id,
        exact_duration=str(datetime.now(UTC)),
        date_short=str(local_user_tz.date()),
        time_of_day=str(local_user_tz.time().isoformat(timespec="minutes")),
    )
    screen = edit if edit_message else answer
    return turn(screen(t("seizure_form.stop_duration"), reply_markup=get_stop_duration_kb()), ack=edit_message)


async def handle_stop_tracking_duration(state, db: AsyncSession, *, edit_message: bool = True) -> FormTurn:
    seizure_data = await state.get_data()
    duration_flag_str = seizure_data.get("exact_duration")
    if duration_flag_str is None:
        return turn(answer(t("seizure_form.restart")), ack=True)
    duration_flag_datetime = datetime.fromisoformat(duration_flag_str.strip('"'))
    duration_diff = int((datetime.now(UTC) - duration_flag_datetime).total_seconds())
    await state.update_data(duration=duration_diff, phase="live")
    return await review_turn(state, db, edit_message=edit_message)
