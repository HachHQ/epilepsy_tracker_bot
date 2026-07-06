from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form.helpers import (
    get_action_btns_flag,
    is_edit_mode,
    load_trigger_keyboard_options,
    save_seizure_edit,
)
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.seizure_kb import (
    generate_features_keyboard,
    get_severity_kb,
    get_temporary_cancel_submit_kb,
)
from services.validators import validate_less_than_250


async def handle_toggle_trigger(callback: CallbackQuery, state, db: AsyncSession):
    _, feature, current_page = callback.data.split(":", 2)
    action_btns_flag = await get_action_btns_flag(state)
    data = await state.get_data()
    selected_triggers = data.get("selected_triggers", [])
    if feature in selected_triggers:
        selected_triggers.remove(feature)
    else:
        selected_triggers.append(feature)
    triggers = await load_trigger_keyboard_options(db, callback.message.chat.id)
    await state.update_data(selected_triggers=selected_triggers)
    await callback.message.edit_text(
        t("seizure_form.select_triggers"),
        reply_markup=generate_features_keyboard(
            triggers,
            selected_triggers,
            current_page,
            5,
            action_btns=action_btns_flag,
        ),
    )
    await callback.answer()


async def handle_triggers_page(callback: CallbackQuery, state, db: AsyncSession):
    data = await state.get_data()
    action_btns_flag = await get_action_btns_flag(state)
    selected_triggers = data.get("selected_triggers", [])
    new_page = callback.data.split(":", 1)[1]
    triggers = await load_trigger_keyboard_options(db, callback.message.chat.id)
    await state.update_data(current_page=new_page)
    await callback.message.edit_text(
        t("seizure_form.select_triggers"),
        reply_markup=generate_features_keyboard(
            features_list=triggers,
            selected_features=selected_triggers,
            current_page=int(new_page),
            page_size=5,
            action_btns=action_btns_flag,
        ),
    )
    await callback.answer()


async def handle_save_toggled_triggers(callback: CallbackQuery, state, db: AsyncSession):
    data = await state.get_data()
    selected_triggers = data.get("selected_triggers", [])
    if await is_edit_mode(state):
        triggers_value = (
            t("seizure_form.triggers_empty")
            if not selected_triggers
            else ", ".join(selected_triggers)
        )
        await save_seizure_edit(
            db,
            callback.message.chat.id,
            state,
            "triggers",
            ",".join(selected_triggers),
        )
        await callback.message.answer(t("seizure_form.triggers_updated", value=triggers_value))
        await callback.answer()
        await state.clear()
        return
    await state.update_data(selected_triggers=selected_triggers)
    await state.set_state(SeizureForm.severity)
    await callback.message.edit_text(t("seizure_form.select_severity"), reply_markup=get_severity_kb())
    await callback.answer()


async def handle_triggers_by_message(message: Message, state, db: AsyncSession):
    if not validate_less_than_250(message.text):
        await message.answer(
            t("seizure_form.triggers_too_long"),
            parse_mode="HTML",
            reply_markup=get_temporary_cancel_submit_kb(),
        )
        return
    data = await state.get_data()
    triggers_list = data.get("selected_triggers", [])
    triggers = message.text if not triggers_list else ", ".join(triggers_list) + ", " + message.text
    if await is_edit_mode(state):
        await save_seizure_edit(db, message.chat.id, state, "triggers", triggers)
        triggers_value = t("seizure_form.triggers_empty") if not triggers else triggers
        await message.answer(t("seizure_form.triggers_updated", value=triggers_value))
        await state.clear()
        return
    await state.update_data(triggers=triggers)
    await state.set_state(SeizureForm.severity)
    await message.answer(t("seizure_form.select_severity"), reply_markup=get_severity_kb())


async def handle_severity(callback: CallbackQuery, state, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    severity = callback.data.split(":")[1]
    if await is_edit_mode(state):
        await save_seizure_edit(db, callback.message.chat.id, state, "severity", severity)
        await callback.message.answer(t("seizure_form.severity_updated", severity=severity))
        await callback.answer()
        await state.clear()
        return
    await state.update_data(severity=severity)
    await callback.message.edit_text(
        t("seizure_form.enter_comment"),
        reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag),
    )
    await state.set_state(SeizureForm.comment)
    await callback.answer()
