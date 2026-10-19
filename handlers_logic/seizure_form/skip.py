from handlers_logic.seizure_form.helpers import load_trigger_keyboard_options
from handlers_logic.seizure_form.screen import FormTurn, answer, edit, turn
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


async def handle_skip_step(state, db, chat_id: int, profile_id: int | None) -> FormTurn:
    current_state = await state.get_state()
    if (current_state is None) or (str(current_state).split(":", 1)[0] != "SeizureForm"):
        return turn(answer(t("seizure_form.restart")), ack=True)
    await state.set_state(SeizureForm.next_state(current_state))
    if current_state == "SeizureForm:hour":
        return turn(edit(t("seizure_form.select_duration"), reply_markup=get_duration_kb()), ack=True)
    if current_state == "SeizureForm:duration":
        return turn(edit(t("seizure_form.select_count"), reply_markup=get_count_of_seizures_kb()), ack=True)
    if current_state == "SeizureForm:count":
        keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
        return turn(answer(t("seizure_form.select_type"), reply_markup=keyboard), ack=True)
    if current_state == "SeizureForm:type_of_seizure":
        triggers = await load_trigger_keyboard_options(db, chat_id, profile_id)
        return turn(
            edit(
                t("seizure_form.select_triggers"),
                reply_markup=generate_features_keyboard(triggers, [], 0, 5),
            ),
            ack=True,
        )
    if current_state == "SeizureForm:triggers":
        return turn(edit(t("seizure_form.select_severity"), reply_markup=get_severity_kb()), ack=True)
    if current_state == "SeizureForm:severity":
        return turn(
            edit(t("seizure_form.enter_comment"), reply_markup=get_temporary_cancel_submit_kb()),
            ack=True,
        )
    if current_state == "SeizureForm:comment":
        return turn(
            edit(t("seizure_form.enter_video"), reply_markup=get_temporary_cancel_submit_kb()),
            ack=True,
        )
    if current_state == "SeizureForm:video_tg_id":
        return turn(
            edit(t("seizure_form.enter_location"), reply_markup=get_temporary_cancel_submit_kb()),
            answer(t("seizure_form.enter_location_or_geo"), reply_markup=get_geolocation_for_timezone_kb()),
            ack=True,
        )
    if current_state == "SeizureForm:location":
        return turn(answer(t("seizure_form.form_complete"), reply_markup=get_final_seizure_btns()), ack=True)
    return turn(ack=True)
