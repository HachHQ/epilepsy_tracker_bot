from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form.helpers import (
    get_action_btns_flag,
    is_edit_mode,
    load_trigger_keyboard_options,
    save_seizure_edit,
)
from handlers_logic.states_factories import SeizureForm
from i18n import get_seizure_types, t
from keyboards.seizure_kb import (
    generate_features_keyboard,
    generate_seizure_type_keyboard,
    get_temporary_cancel_submit_kb,
)
from services.validators import validate_non_neg_N_num


async def handle_count_of_seizures(callback: CallbackQuery, state, db: AsyncSession):
    count_of_seizures = int(callback.data.split(":", 1)[1])
    if await is_edit_mode(state):
        await save_seizure_edit(db, callback.message.chat.id, state, "count", count_of_seizures)
        await callback.message.answer(t("seizure_form.count_updated", value=count_of_seizures))
        await callback.answer()
        await state.clear()
        return
    await state.update_data(count=count_of_seizures)
    await state.set_state(SeizureForm.type_of_seizure)
    keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
    await callback.message.edit_text(t("seizure_form.select_type"), reply_markup=keyboard)
    await callback.answer()


async def handle_count_by_message(message: Message, state, db: AsyncSession):
    if not validate_non_neg_N_num(message.text):
        await message.answer(
            t("seizure_form.invalid_count"),
            parse_mode="HTML",
            reply_markup=get_temporary_cancel_submit_kb(),
        )
        return
    count = int(message.text)
    if await is_edit_mode(state):
        await save_seizure_edit(db, message.chat.id, state, "count", count)
        await message.answer(t("seizure_form.count_updated", value=count))
        await state.clear()
        return
    await state.update_data(count=message.text)
    await state.set_state(SeizureForm.type_of_seizure)
    keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
    await message.answer(t("seizure_form.select_type"), reply_markup=keyboard)


async def handle_type_of_seizure_page(callback: CallbackQuery, state, db: AsyncSession):
    _, current_page = callback.data.split(":", 1)
    keyboard = generate_seizure_type_keyboard(current_page=current_page, page_size=6)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


async def handle_type_of_seizure_save(callback: CallbackQuery, state, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    type_of_seizure_id = callback.data.split(":", 1)[1]
    seizure_type = get_seizure_types()[int(type_of_seizure_id)]
    if await is_edit_mode(state):
        await save_seizure_edit(db, callback.message.chat.id, state, "type_of_seizure", seizure_type)
        await callback.message.answer(t("seizure.type_updated", seizure_type=seizure_type))
        await state.clear()
        return
    await state.update_data(type_of_seizure=seizure_type)
    await state.set_state(SeizureForm.triggers)
    await state.update_data(selected_triggers=[], current_page=0)
    triggers = await load_trigger_keyboard_options(db, callback.message.chat.id)
    await callback.message.edit_text(
        t("seizure_form.select_triggers"),
        reply_markup=generate_features_keyboard(triggers, [], 0, 5, action_btns=action_btns_flag),
    )
    await callback.answer()
