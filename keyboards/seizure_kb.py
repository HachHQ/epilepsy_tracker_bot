import calendar
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timezone, timedelta

cancel_seizure_menu_btn = InlineKeyboardButton(text="❌ Отменить заполнение", callback_data="cancel_fix_seizure_menu")

def get_year_date_kb(backward_offset: int = 3, forward_offset: int = 1):
    current_datetime = datetime.now(timezone.utc)
    one_day_ago = current_datetime - timedelta(days=1)
    two_day_ago = current_datetime - timedelta(days=2)
    current_year = current_datetime.date().year
    years_date_kb_bd = InlineKeyboardBuilder()

    for year in range(current_year - backward_offset, current_year + forward_offset + 1):
        years_date_kb_bd.button(text=f"{year}", callback_data=f"year:{year}")
    years_date_kb_bd.adjust(5)

    two_day_btn = InlineKeyboardButton(text="Позавчера", callback_data=f"year:two_d_ago")
    one_day_ago_btn = InlineKeyboardButton(text="Вчера", callback_data=f"year:one_d_ago")
    today_btn = InlineKeyboardButton(text="Сегодня", callback_data=f"year:today")
    years_date_kb_bd.row(two_day_btn, one_day_ago_btn, today_btn)
    years_date_kb_bd.row(cancel_seizure_menu_btn)
    return years_date_kb_bd.as_markup()

def get_profiles_for_seizure_fix(list: list[str]) -> InlineKeyboardMarkup:
    profiles_kb_bd = InlineKeyboardBuilder()
    back_btn = InlineKeyboardButton(text="⬅️ Назад", callback_data="back:to_menu")
    if not list:
        offer_to_create_profile_btn = InlineKeyboardButton(text="Создать профиль", callback_data="to_filling_profile_form")
        profiles_kb_bd.row(offer_to_create_profile_btn)
        profiles_kb_bd.row(back_btn)
        return profiles_kb_bd.as_markup()
    for profile in list:
        profiles_kb_bd.button(text=f"{profile.profile_name}", callback_data=f"fix_seizure:{profile.id}:{profile.profile_name}")
    profiles_kb_bd.adjust(1)
    profiles_kb_bd.row(back_btn)

    return profiles_kb_bd.as_markup()

def get_month_date_kb() -> InlineKeyboardMarkup:
    month_kb_bd = InlineKeyboardBuilder()
    for i in range(1, 13):
        month_kb_bd.button(text=calendar.month_name[i], callback_data=f"month:{i}")
    month_kb_bd.adjust(3)
    back_btn = InlineKeyboardButton(text="⬅️ Назад", callback_data="back:year")
    month_kb_bd.row(back_btn)
    return month_kb_bd.as_markup()

def get_hour_date_kb() -> InlineKeyboardMarkup:
    hour_kb_bd = InlineKeyboardBuilder()


def get_day_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    # Узнаем количество дней в месяце
    kb_builder = InlineKeyboardBuilder()
    days_in_month = calendar.monthrange(year, month)[1]
    for day in range(1, days_in_month + 1):
        kb_builder.button(text=str(day), callback_data=f"day:{day}")
    # Распределяем кнопки по строкам (по 7 в строке)
    kb_builder.button(text="↩ Назад", callback_data="go_back")
    kb_builder.adjust(7)
    return kb_builder.as_markup()
