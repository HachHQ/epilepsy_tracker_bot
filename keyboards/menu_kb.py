from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from lexicon.lexicon import LEXICON_BUTTONS

def get_cancel_kb() -> InlineKeyboardMarkup:
    cancel_bd = InlineKeyboardBuilder()
    cancel_bd.button(text=LEXICON_BUTTONS['cancel'], callback_data='cancel_fsm_script')
    return cancel_bd.as_markup()

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text="Зафиксировать приступ",
        callback_data="menu:choose_profile"
    )
    kb_builder.button(
        text="Журнал личный",
        callback_data="menu:seizure_log"
    )
    kb_builder.button(
        text="Журнал ДЛ",
        callback_data="menu:trusted_log"
    )
    kb_builder.button(
        text="Профили",
        callback_data="menu:choose_profile"
    )
    kb_builder.button(
        text="Уведомления",
        callback_data="menu:set_notifications"
    )
    kb_builder.button(
        text="Добавить ДЛ",
        callback_data="menu:add_trusted"
    )
    kb_builder.button(
        text="Импортировать данные",
        callback_data="menu:import_log"
    )
    kb_builder.adjust(2)
    return kb_builder.as_markup()