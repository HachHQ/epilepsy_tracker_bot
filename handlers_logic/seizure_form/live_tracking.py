from datetime import UTC, datetime

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.users import get_user_by_chat_id
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.seizure_kb import get_count_of_seizures_kb, get_stop_duration_kb
from services.notes_formatters import get_minutes_and_seconds
from services.user_timezone import get_local_time_from_offset


async def handle_seizre_right_now(message: Message, state, db: AsyncSession):
    await state.clear()
    user = await get_user_by_chat_id(db, message.chat.id)
    local_user_tz = get_local_time_from_offset(int(user.timezone))
    await state.update_data(exact_duration=str(datetime.now(UTC)))
    await state.update_data(date_short=str(local_user_tz.date()))
    await state.update_data(time_of_day=str(local_user_tz.time().isoformat(timespec="minutes")))
    await message.answer(t("seizure_form.stop_duration"), reply_markup=get_stop_duration_kb())


async def handle_stop_tracking_duration(message: Message, state):
    seizure_data = await state.get_data()
    duration_flag_str = seizure_data.get("exact_duration")
    if duration_flag_str is None:
        await message.answer(t("seizure_form.restart"))
        return
    duration_flag_datetime = datetime.fromisoformat(duration_flag_str.strip('"'))
    duration_diff = int((datetime.now(UTC) - duration_flag_datetime).total_seconds())
    await state.update_data(duration=duration_diff)
    await message.edit_text(t("seizure_form.count_series"), reply_markup=get_count_of_seizures_kb())
    await message.answer(t("seizure_form.duration_recorded", duration=get_minutes_and_seconds(duration_diff)))
    await state.set_state(SeizureForm.count)
