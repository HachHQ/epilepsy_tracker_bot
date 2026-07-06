from aiogram.types import Message

from handlers_logic.seizure_form.helpers import load_trigger_keyboard_options
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb
from keyboards.seizure_kb import (
    generate_features_keyboard,
    generate_seizure_type_keyboard,
    get_count_of_seizures_kb,
    get_duration_kb,
    get_final_seizure_btns,
    get_severity_kb,
    get_temporary_cancel_submit_kb,
)


async def handle_skip_step(message: Message, state, db):
    current_state = await state.get_state()
    if (current_state is None) or (str(current_state).split(":", 1)[0] != "SeizureForm"):
        return await message.answer(t("seizure_form.restart"))
    await state.set_state(SeizureForm.next_state(current_state))
    if current_state == "SeizureForm:hour":
        await message.edit_text(t("seizure_form.select_duration"), reply_markup=get_duration_kb())
    elif current_state == "SeizureForm:duration":
        await message.edit_text(t("seizure_form.select_count"), reply_markup=get_count_of_seizures_kb())
    elif current_state == "SeizureForm:count":
        keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
        await message.answer(t("seizure_form.select_type"), reply_markup=keyboard)
    elif current_state == "SeizureForm:type_of_seizure":
        triggers = await load_trigger_keyboard_options(db, message.chat.id)
        await message.edit_text(
            t("seizure_form.select_triggers"),
            reply_markup=generate_features_keyboard(triggers, [], 0, 5),
        )
    elif current_state == "SeizureForm:triggers":
        await message.edit_text(t("seizure_form.select_severity"), reply_markup=get_severity_kb())
    elif current_state == "SeizureForm:severity":
        await message.edit_text(t("seizure_form.enter_comment"), reply_markup=get_temporary_cancel_submit_kb())
    elif current_state == "SeizureForm:comment":
        await message.edit_text(t("seizure_form.enter_video"), reply_markup=get_temporary_cancel_submit_kb())
    elif current_state == "SeizureForm:video_tg_id":
        await message.edit_text(t("seizure_form.enter_location"), reply_markup=get_temporary_cancel_submit_kb())
        await message.answer(t("seizure_form.enter_location_or_geo"), reply_markup=get_geolocation_for_timezone_kb())
    elif current_state == "SeizureForm:location":
        await message.answer(t("seizure_form.form_complete"), reply_markup=get_final_seizure_btns())
