from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from datetime import datetime, timezone, timedelta


#TODO finish this function
def get_year_date_kb(backward_offset: int = 4, forward_offset: int = 1):
    current_datetime = datetime.now(timezone.utc)
    yesterday = current_datetime - timedelta(days=1)
    tomorrow = current_datetime + timedelta(days=1)
    current_year = current_datetime.date().year
    years_date_kb_bd = InlineKeyboardBuilder()
    for year in range(current_year - backward_offset, current_year + forward_offset + 1):
        years_date_kb_bd.button(text=f"{year}", callback_data=f"date:{year}")
    years_date_kb_bd.adjust()
    return years_date_kb_bd.as_markup()