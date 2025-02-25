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
        callback_data="menu:fix_attack"
    )
    kb_builder.button(
        text="Журнал приступов",
        callback_data="menu:seizure_log"
    )
    kb_builder.button(
        text="Журнал доверенных лиц",
        callback_data="menu:trusted_log"
    )
    kb_builder.button(
        text="Редактировать профиль",
        callback_data="menu:edit_profile"
    )
    kb_builder.button(
        text="Настроить уведомления",
        callback_data="menu:set_notifications"
    )
    kb_builder.button(
        text="Добавить доверенное лицо",
        callback_data="menu:add_trusted"
    )
    kb_builder.button(
        text="Импортировать журнал приступов",
        callback_data="menu:import_log"
    )
    kb_builder.adjust(2)
    return kb_builder.as_markup()