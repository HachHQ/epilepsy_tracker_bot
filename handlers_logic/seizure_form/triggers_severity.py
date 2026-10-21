from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form.card import finish_edit
from handlers_logic.seizure_form.helpers import (
    get_action_btns_flag,
    is_edit_mode,
    load_trigger_keyboard_options,
    save_seizure_edit,
)
from handlers_logic.seizure_form.screen import FormTurn, answer, edit, turn
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.seizure_kb import (
    generate_features_keyboard,
    get_severity_kb,
    get_temporary_cancel_submit_kb,
)
from services.validators import validate_less_than_250


async def handle_toggle_trigger(
    state, db: AsyncSession, chat_id: int, profile_id: int | None, data: str
) -> FormTurn:
    _, feature, current_page = data.split(":", 2)
    action_btns_flag = await get_action_btns_flag(state)
    stored = await state.get_data()
    selected_triggers = stored.get("selected_triggers", [])
    if feature in selected_triggers:
        selected_triggers.remove(feature)
    else:
        selected_triggers.append(feature)
    triggers = await load_trigger_keyboard_options(db, chat_id, profile_id)
    await state.update_data(selected_triggers=selected_triggers)
    return turn(
        edit(
            t("seizure_form.select_triggers"),
            reply_markup=generate_features_keyboard(
                triggers,
                selected_triggers,
                int(current_page),
                5,
                action_btns=action_btns_flag,
            ),
        ),
        ack=True,
    )


async def handle_triggers_page(
    state, db: AsyncSession, chat_id: int, profile_id: int | None, data: str
) -> FormTurn:
    stored = await state.get_data()
    action_btns_flag = await get_action_btns_flag(state)
    selected_triggers = stored.get("selected_triggers", [])
    new_page = data.split(":", 1)[1]
    triggers = await load_trigger_keyboard_options(db, chat_id, profile_id)
    await state.update_data(current_page=new_page)
    return turn(
        edit(
            t("seizure_form.select_triggers"),
            reply_markup=generate_features_keyboard(
                features_list=triggers,
                selected_features=selected_triggers,
                current_page=int(new_page),
                page_size=5,
                action_btns=action_btns_flag,
            ),
        ),
        ack=True,
    )


async def handle_save_toggled_triggers(state, db: AsyncSession, chat_id: int) -> FormTurn:
    stored = await state.get_data()
    selected_triggers = stored.get("selected_triggers", [])
    if await is_edit_mode(state):
        triggers_value = (
            t("seizure_form.triggers_empty")
            if not selected_triggers
            else ", ".join(selected_triggers)
        )
        await save_seizure_edit(db, chat_id, state, "triggers", ",".join(selected_triggers))
        return await finish_edit(
            state, db, answer(t("seizure_form.triggers_updated", value=triggers_value)), ack=True
        )
    await state.update_data(selected_triggers=selected_triggers)
    await state.set_state(SeizureForm.severity)
    return turn(edit(t("seizure_form.select_severity"), reply_markup=get_severity_kb()), ack=True)


async def handle_triggers_by_message(state, db: AsyncSession, chat_id: int, text: str | None) -> FormTurn:
    if not validate_less_than_250(text or ""):
        return turn(
            answer(
                t("seizure_form.triggers_too_long"),
                parse_mode="HTML",
                reply_markup=get_temporary_cancel_submit_kb(),
            )
        )
    stored = await state.get_data()
    triggers_list = stored.get("selected_triggers", [])
    triggers = text if not triggers_list else ", ".join(triggers_list) + ", " + (text or "")
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "triggers", triggers)
        triggers_value = t("seizure_form.triggers_empty") if not triggers else triggers
        return await finish_edit(
            state, db, answer(t("seizure_form.triggers_updated", value=triggers_value)), ack=False
        )
    await state.update_data(triggers=triggers)
    await state.set_state(SeizureForm.severity)
    return turn(answer(t("seizure_form.select_severity"), reply_markup=get_severity_kb()))


async def handle_severity(state, db: AsyncSession, chat_id: int, data: str) -> FormTurn:
    action_btns_flag = await get_action_btns_flag(state)
    severity = data.split(":")[1]
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "severity", severity)
        return await finish_edit(
            state, db, answer(t("seizure_form.severity_updated", severity=severity)), ack=True
        )
    await state.update_data(severity=severity)
    await state.set_state(SeizureForm.comment)
    return turn(
        edit(
            t("seizure_form.enter_comment"),
            reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
        ),
        ack=True,
    )
