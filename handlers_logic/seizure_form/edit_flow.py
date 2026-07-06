from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form import ask_for_a_year
from handlers_logic.seizure_form.helpers import load_trigger_keyboard_options
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb
from keyboards.seizure_kb import (
    generate_features_keyboard,
    generate_seizure_type_keyboard,
    get_count_of_seizures_kb,
    get_duration_kb,
    get_severity_kb,
    get_time_ranges_kb,
)


async def start_seizure_field_edit(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    *,
    action: str,
    seizure_id: int,
    profile_id: int,
) -> None:
    await state.update_data(mode="edit", seizure_id=seizure_id, profile_id=profile_id)

    if action == "date":
        await ask_for_a_year(message, state)
        await state.set_state(SeizureForm.year)
    elif action == "time":
        await message.answer(t("journal.edit_time"), reply_markup=get_time_ranges_kb(action_btns=False))
        await state.set_state(SeizureForm.hour)
    elif action == "count":
        await message.answer(t("journal.edit_count"), reply_markup=get_count_of_seizures_kb(action_btns=False))
        await state.set_state(SeizureForm.count)
    elif action == "type":
        await state.set_state(SeizureForm.type_of_seizure)
        keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6, action_btns=False)
        await message.answer(t("journal.edit_type"), reply_markup=keyboard)
    elif action == "triggers":
        await state.update_data(selected_triggers=[], current_page=0)
        triggers = await load_trigger_keyboard_options(db, message.chat.id)
        await message.answer(
            t("journal.edit_triggers"),
            reply_markup=generate_features_keyboard(triggers, [], 0, 5, action_btns=False),
        )
        await state.set_state(SeizureForm.triggers)
    elif action == "severity":
        await message.answer(t("journal.edit_severity"), reply_markup=get_severity_kb(action_btns=False))
        await state.set_state(SeizureForm.severity)
    elif action == "duration":
        await message.answer(t("journal.edit_duration"), reply_markup=get_duration_kb(action_btns=False))
        await state.set_state(SeizureForm.duration)
    elif action == "comment":
        await message.answer(t("journal.edit_comment"))
        await state.set_state(SeizureForm.comment)
    elif action == "video":
        await message.answer(t("journal.edit_video"))
        await state.set_state(SeizureForm.video_tg_id)
    elif action == "location":
        await message.answer(t("journal.edit_location"), reply_markup=get_geolocation_for_timezone_kb())
        await state.set_state(SeizureForm.location)
    else:
        await message.answer(t("journal.unknown_command"))
