from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton

from lexicon.lexicon import LEXICON_BUTTONS

def get_cancel_kb() -> InlineKeyboardMarkup:
    cancel_bd = InlineKeyboardBuilder()
    cancel_bd.button(text=LEXICON_BUTTONS['cancel'], callback_data='cancel_fsm_script')
    return cancel_bd.as_markup()

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    panic_btn = InlineKeyboardButton(text="⚠️ Аура", callback_data="aura_notification")
    fix_btn = InlineKeyboardButton(text="✏️ Зафиксировать приступ", callback_data="fix_seizure")
    journal_btn = InlineKeyboardButton(text="📖 Журнал", callback_data="seizure_log")
    profiles_btn = InlineKeyboardButton(text="👤 Профили", callback_data="choose_profile")
    add_trusted_person_btn = InlineKeyboardButton(text="🙍 Добавить ДЛ",callback_data="add_trusted")
    notification_btn = InlineKeyboardButton(text="🔔 Уведомления", callback_data="set_notifications")
    import_btn = InlineKeyboardButton(text="⬇️ Импортировать", callback_data="import_log")
    kb_builder.row(panic_btn)
    kb_builder.row(fix_btn)
    kb_builder.row(profiles_btn, notification_btn)
    kb_builder.row(journal_btn)
    kb_builder.row(add_trusted_person_btn, import_btn)
    return kb_builder.as_markup()