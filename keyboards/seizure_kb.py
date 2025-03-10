from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from datetime import datetime, timezone, timedelta


#TODO finish this function
def get_year_date_kb(backward_offset: int = 4, forward_offset: int = 1):
    current_datetime = datetime.now(timezone.utc)
    one_day_ago = current_datetime - timedelta(days=1)
    two_day_ago = current_datetime - timedelta(days=2)
    current_year = current_datetime.date().year
    years_date_kb_bd = InlineKeyboardBuilder()

    for year in range(current_year - backward_offset, current_year + forward_offset + 1):
        years_date_kb_bd.button(text=f"{year}", callback_data=f"date:{year}")
    years_date_kb_bd.adjust(5)

    two_day_btn = InlineKeyboardButton(text="Позавчера", callback_data=f"date:two_d_ago:{two_day_ago.date()}")
    one_day_ago_btn = InlineKeyboardButton(text="Вчера", callback_data=f"date:one_d_ago:{one_day_ago.date()}")
    today_btn = InlineKeyboardButton(text="Сегодня", callback_data=f"date:today:{current_datetime.date()}")
    years_date_kb_bd.row(two_day_btn, one_day_ago_btn, today_btn)

    back_btn = InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:choose_profile")
    years_date_kb_bd.row(back_btn)


    return years_date_kb_bd.as_markup()