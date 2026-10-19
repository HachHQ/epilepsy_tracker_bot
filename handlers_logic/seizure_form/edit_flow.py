from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.seizures import get_seizure_by_id
from handlers_logic.seizure_form.datetime_steps import ask_for_a_year
from handlers_logic.seizure_form.helpers import (
    load_symptom_keyboard_options,
    load_trigger_keyboard_options,
    selected_symptom_names,
)
from handlers_logic.seizure_form.screen import FormTurn, answer, turn
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
    state,
    db: AsyncSession,
    *,
    action: str,
    seizure_id: int,
    profile_id: int,
    chat_id: int,
) -> FormTurn:
    await state.update_data(mode="edit", seizure_id=seizure_id, profile_id=profile_id)

    if action == "date":
        year_turn = await ask_for_a_year(state)
        await state.set_state(SeizureForm.year)
        return year_turn
    if action == "time":
        await state.set_state(SeizureForm.hour)
        return turn(answer(t("journal.edit_time"), reply_markup=get_time_ranges_kb(action_btns=False)))
    if action == "count":
        await state.set_state(SeizureForm.count)
        return turn(answer(t("journal.edit_count"), reply_markup=get_count_of_seizures_kb(action_btns=False)))
    if action == "type":
        await state.set_state(SeizureForm.type_of_seizure)
        keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6, action_btns=False)
        return turn(answer(t("journal.edit_type"), reply_markup=keyboard))
    if action == "triggers":
        await state.update_data(selected_triggers=[], current_page=0)
        triggers = await load_trigger_keyboard_options(db, chat_id, profile_id)
        await state.set_state(SeizureForm.triggers)
        return turn(
            answer(
                t("journal.edit_triggers"),
                reply_markup=generate_features_keyboard(triggers, [], 0, 5, action_btns=False),
            )
        )
    if action == "severity":
        await state.set_state(SeizureForm.severity)
        return turn(answer(t("journal.edit_severity"), reply_markup=get_severity_kb(action_btns=False)))
    if action == "duration":
        await state.set_state(SeizureForm.duration)
        return turn(answer(t("journal.edit_duration"), reply_markup=get_duration_kb(action_btns=False)))
    if action == "comment":
        await state.set_state(SeizureForm.comment)
        return turn(answer(t("journal.edit_comment")))
    if action == "symptoms":
        seizure = await get_seizure_by_id(db, seizure_id, profile_id)
        selected = selected_symptom_names(None if seizure is None else seizure.symptoms)
        await state.update_data(selected_symptoms=selected, current_page=0)
        options = await load_symptom_keyboard_options(db, chat_id, profile_id, selected)
        await state.set_state(SeizureForm.symptoms)
        return turn(
            answer(
                t("journal.edit_symptoms"),
                reply_markup=generate_features_keyboard(options, selected, 0, 5, action_btns=False),
            )
        )
    if action == "video":
        await state.set_state(SeizureForm.video_tg_id)
        return turn(answer(t("journal.edit_video")))
    if action == "location":
        await state.set_state(SeizureForm.location)
        return turn(answer(t("journal.edit_location"), reply_markup=get_geolocation_for_timezone_kb()))
    return turn(answer(t("journal.unknown_command")))
