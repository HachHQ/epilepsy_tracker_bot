from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.seizure_form.card import finish_edit
from handlers_logic.seizure_form.helpers import (
    get_action_btns_flag,
    is_edit_mode,
    load_symptom_keyboard_options,
    save_seizure_edit,
    selected_symptom_names,
)
from handlers_logic.seizure_form.screen import FormTurn, answer, edit, turn
from i18n import t
from keyboards.seizure_kb import generate_features_keyboard, get_temporary_cancel_submit_kb
from services.validators import validate_less_than_250


def _stored_value(names: list[str]) -> str:
    return ", ".join(names)


def _display_value(names: list[str]) -> str:
    if not names:
        return t("seizure_form.symptoms_empty")
    return _stored_value(names)


async def handle_toggle_symptom(
    state, db: AsyncSession, chat_id: int, profile_id: int | None, data: str
) -> FormTurn:
    _, feature, current_page = data.split(":", 2)
    action_btns_flag = await get_action_btns_flag(state)
    stored = await state.get_data()
    selected = list(stored.get("selected_symptoms", []))
    if feature in selected:
        selected.remove(feature)
    else:
        selected.append(feature)
    options = await load_symptom_keyboard_options(db, chat_id, profile_id, selected)
    await state.update_data(selected_symptoms=selected)
    return turn(
        edit(
            t("seizure_form.select_symptoms"),
            reply_markup=generate_features_keyboard(
                options,
                selected,
                int(current_page),
                5,
                action_btns=action_btns_flag,
            ),
        ),
        ack=True,
    )


async def handle_symptoms_page(
    state, db: AsyncSession, chat_id: int, profile_id: int | None, data: str
) -> FormTurn:
    stored = await state.get_data()
    action_btns_flag = await get_action_btns_flag(state)
    selected = stored.get("selected_symptoms", [])
    new_page = data.split(":", 1)[1]
    options = await load_symptom_keyboard_options(db, chat_id, profile_id, selected)
    await state.update_data(current_page=new_page)
    return turn(
        edit(
            t("seizure_form.select_symptoms"),
            reply_markup=generate_features_keyboard(
                features_list=options,
                selected_features=selected,
                current_page=int(new_page),
                page_size=5,
                action_btns=action_btns_flag,
            ),
        ),
        ack=True,
    )


async def handle_save_symptoms(state, db: AsyncSession, chat_id: int) -> FormTurn:
    stored = await state.get_data()
    selected = selected_symptom_names(stored.get("selected_symptoms", []))
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "symptoms", _stored_value(selected))
        return await finish_edit(
            state,
            db,
            answer(t("seizure_form.symptoms_updated", value=_display_value(selected))),
            ack=True,
        )
    return turn(ack=True)


async def handle_symptoms_by_message(
    state, db: AsyncSession, chat_id: int, text: str | None
) -> FormTurn:
    if not validate_less_than_250(text or ""):
        return turn(
            answer(
                t("seizure_form.symptoms_too_long"),
                parse_mode="HTML",
                reply_markup=get_temporary_cancel_submit_kb(),
            )
        )
    stored = await state.get_data()
    selected = selected_symptom_names(stored.get("selected_symptoms", []))
    typed = selected_symptom_names(text)
    names = list(dict.fromkeys([*selected, *typed]))
    if await is_edit_mode(state):
        await save_seizure_edit(db, chat_id, state, "symptoms", _stored_value(names))
        return await finish_edit(
            state,
            db,
            answer(t("seizure_form.symptoms_updated", value=_display_value(names))),
            ack=False,
        )
    return turn(ack=True)
