import calendar
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timezone, timedelta

cancel_seizure_menu_btn = InlineKeyboardButton(text="❌ Отменить заполнение", callback_data="cancel_fsm_script")
confirm_seizure_data_btn = InlineKeyboardButton(text="✅ Подтвердить", callback_data="check_input_seizure_data")

def get_temporary_cancel_submit_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(cancel_seizure_menu_btn)
    builder.row(confirm_seizure_data_btn)
    return builder.as_markup()

def get_year_date_kb(backward_offset: int = 3, forward_offset: int = 1):
    current_datetime = datetime.now(timezone.utc)
    current_year = current_datetime.date().year
    years_date_kb_bd = InlineKeyboardBuilder()
    t_d_ago_date = current_datetime - timedelta(days=2)
    o_d_ago_date = current_datetime - timedelta(days=1)
    for year in range(current_year - backward_offset, current_year + forward_offset + 1):
        years_date_kb_bd.button(text=f"{year}", callback_data=f"year:{year}")
    years_date_kb_bd.adjust(5)

    two_day_btn = InlineKeyboardButton(text="Позавчера", callback_data=f"year:two_d_ago/{t_d_ago_date.date()}")
    one_day_ago_btn = InlineKeyboardButton(text="Вчера", callback_data=f"year:one_d_ago/{o_d_ago_date.date()}")
    today_btn = InlineKeyboardButton(text="Сегодня", callback_data=f"year:today/{current_datetime.date()}")
    years_date_kb_bd.row(two_day_btn, one_day_ago_btn, today_btn)
    years_date_kb_bd.row(cancel_seizure_menu_btn)
    return years_date_kb_bd.as_markup()

def get_month_date_kb() -> InlineKeyboardMarkup:
    month_kb_bd = InlineKeyboardBuilder()
    month_in_russian = ['Январь', 'Февраль', 'Март', 'Апрьель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    for i in range(1, 13):
        month_kb_bd.button(text=month_in_russian[i-1], callback_data=f"month:{i}:{month_in_russian[i-1]}")
    month_kb_bd.adjust(3)
    month_kb_bd.row(cancel_seizure_menu_btn)
    return month_kb_bd.as_markup()


def get_day_kb(year: int, month: int) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    days_in_month = calendar.monthrange(year, month)[1]
    for day in range(1, days_in_month + 1):
        kb_builder.button(text=str(day), callback_data=f"day:{day}")
    kb_builder.adjust(7)
    kb_builder.row(cancel_seizure_menu_btn)
    return kb_builder.as_markup()

def get_times_of_day_kb() -> InlineKeyboardMarkup:
    times_of_day_kb_bd = InlineKeyboardBuilder()
    times_of_day = ['Утро', 'День', 'Вечер', 'Ночь']
    for part in times_of_day:
        times_of_day_kb_bd.button(text=f"{part}", callback_data=f"time_of_day:{part}")
    times_of_day_kb_bd.adjust(2)
    times_of_day_kb_bd.row(cancel_seizure_menu_btn)
    times_of_day_kb_bd.row(confirm_seizure_data_btn)
    return times_of_day_kb_bd.as_markup()

def get_severity_kb() -> InlineKeyboardMarkup:
    severity_kb_db = InlineKeyboardBuilder()
    list_of_severity = {'Легкий':'light', 'Средний':'medium', 'Тяжелый':'heavy'}
    for text, cd_value in list_of_severity.items():
        severity_kb_db.button(text=f"{text}", callback_data=f"saverity:{cd_value}")
    severity_kb_db.row(cancel_seizure_menu_btn)
    severity_kb_db.row(confirm_seizure_data_btn)
    return severity_kb_db.as_markup()
