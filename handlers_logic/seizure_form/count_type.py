from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form.card import finish_edit, review_turn
from handlers_logic.seizure_form.helpers import (
    get_action_btns_flag,
    is_edit_mode,
    load_trigger_keyboard_options,
    save_seizure_edit,
)
from handlers_logic.seizure_form.screen import FormTurn, answer, edit, edit_markup, turn
from handlers_logic.states_factories import SeizureForm
from i18n import get_seizure_types, t
from keyboards.seizure_kb import (
    generate_features_keyboard,
    generate_seizure_type_keyboard,
    get_temporary_cancel_submit_kb,
)
from services.validators import validate_non_neg_N_num


async def handle_count_of_seizures(state, db: AsyncSession, chat_id: int, data: str) -> FormTurn:
    count_of_seizures = int(data.split(":", 1)[1])
    stored = await state.get_data()
    if stored.get("return_to_review"):
        await state.update_data(count=count_of_seizures, return_to_review=False)
        return await review_turn(state, db, edit_message=True)
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "count", count_of_seizures)
        return await finish_edit(
            state, db, answer(t("seizure_form.count_updated", value=count_of_seizures)), ack=True
        )
    await state.update_data(count=count_of_seizures)
    await state.set_state(SeizureForm.type_of_seizure)
    keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
    return turn(edit(t("seizure_form.select_type"), reply_markup=keyboard), ack=True)


async def handle_count_by_message(state, db: AsyncSession, chat_id: int, text: str | None) -> FormTurn:
    if not validate_non_neg_N_num(text or ""):
        return turn(
            answer(
                t("seizure_form.invalid_count"),
                parse_mode="HTML",
                reply_markup=get_temporary_cancel_submit_kb(),
            )
        )
    count = int(text or "0")
    if (await state.get_data()).get("return_to_review"):
        await state.update_data(count=count, return_to_review=False)
        return await review_turn(state, db, edit_message=False)
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "count", count)
        return await finish_edit(state, db, answer(t("seizure_form.count_updated", value=count)), ack=False)
    await state.update_data(count=text)
    await state.set_state(SeizureForm.type_of_seizure)
    keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
    return turn(answer(t("seizure_form.select_type"), reply_markup=keyboard))


async def handle_type_of_seizure_page(data: str, *, back: bool = False) -> FormTurn:
    _, current_page = data.split(":", 1)
    keyboard = generate_seizure_type_keyboard(current_page=int(current_page), page_size=6, action_btns=not back, back=back)
    return turn(edit_markup(keyboard), ack=True)


async def handle_type_of_seizure_save(
    state, db: AsyncSession, chat_id: int, profile_id: int | None, data: str
) -> FormTurn:
    action_btns_flag = await get_action_btns_flag(state)
    type_of_seizure_id = data.split(":", 1)[1]
    seizure_type = get_seizure_types()[int(type_of_seizure_id)]
    stored = await state.get_data()
    if stored.get("return_to_review"):
        await state.update_data(type_of_seizure=seizure_type, return_to_review=False, from_last=False)
        return await review_turn(state, db, edit_message=True)
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "type_of_seizure", seizure_type)
        return await finish_edit(
            state, db, answer(t("seizure.type_updated", seizure_type=seizure_type)), ack=True
        )
    await state.update_data(type_of_seizure=seizure_type)
    await state.set_state(SeizureForm.triggers)
    await state.update_data(selected_triggers=[], current_page=0)
    triggers = await load_trigger_keyboard_options(db, chat_id, profile_id)
    return turn(
        edit(
            t("seizure_form.select_triggers"),
            reply_markup=generate_features_keyboard(triggers, [], 0, 5, action_btns=action_btns_flag),
        ),
        ack=True,
    )
