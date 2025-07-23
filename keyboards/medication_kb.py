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

def get_skip_cancel_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить действие", callback_data='cancel_fsm_script')
    builder.button(text="⏩ Пропустить шаг", callback_data="skip_note_for_medication")
    builder.adjust(1)
    return builder.as_markup()

def get_actual_med_cancel_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить действие", callback_data='cancel_fsm_script')
    builder.button(text="⌛ Еще принимаю", callback_data="skip_end_date_for_medication")
    builder.adjust(1)
    return builder.as_markup()

def get_deleting_medication_kb(mdc_id, prof_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=f'delete_med_prof:yes:{mdc_id}:{prof_id}')
    builder.button(text="Нет", callback_data=f"delete_med_prof:no:{mdc_id}:{prof_id}")
    builder.adjust(1)
    return builder.as_markup()