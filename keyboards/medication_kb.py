from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, KeyboardButton

def get_medication_sumbenu():
    builder = InlineKeyboardBuilder()
    builder.button(text="✚ Добавить препарат", callback_data="add_medication")
    builder.button(text="⚙️ Управление", callback_data="medication_settings")
    builder.button(text="↩️ Назад", callback_data="to_menu_edit")
    builder.adjust(1)
    return builder.as_markup()