from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from lexicon.lexicon import LEXICON_BUTTONS

def get_cancel_kb() -> InlineKeyboardMarkup:
    cancel_bd = InlineKeyboardBuilder()
    cancel_bd.button(text=LEXICON_BUTTONS['cancel'], callback_data='cancel_fsm_script')
    return cancel_bd.as_markup()

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    panic_btn = InlineKeyboardButton(text="🆘 Экстренное уведомление", callback_data="sos_notification")
    fix_btn = InlineKeyboardButton(text="✏️ Зафиксировать приступ", callback_data="fix_seizure")
    journal_btn = InlineKeyboardButton(text="🗂️ Данные о приступах", callback_data="seizure_data")
    profiles_btn = InlineKeyboardButton(text="👤 Выбрать профиль", callback_data="choose_profile")
    control_profiles = InlineKeyboardButton(text="⚙️ Управление",callback_data="control_profiles")
    notification_btn = InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications_control")
    import_btn = InlineKeyboardButton(text="💊 Медицина", callback_data="medication")
    kb_builder.row(panic_btn)
    kb_builder.row(fix_btn)
    kb_builder.row(profiles_btn, notification_btn)
    kb_builder.row(journal_btn)
    kb_builder.row(control_profiles, import_btn)
    return kb_builder.as_markup()