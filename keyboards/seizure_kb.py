import calendar
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timezone, timedelta

from lexicon.lexicon import LEXICON_EPILEPSY_TRIGGERS
cancel_seizure_menu_btn = InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_fsm_script")
confirm_seizure_data_btn = InlineKeyboardButton(text="✅ Подтвердить", callback_data="check_input_seizure_data")

def get_temporary_cancel_submit_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(cancel_seizure_menu_btn)
    builder.row(confirm_seizure_data_btn)
    builder.adjust(2)
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
    month_in_russian = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
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
    severity_bd = InlineKeyboardBuilder()
    for i in range(1, 11):
        severity_bd.button(text=f"{i}", callback_data=f"saverity:{i}")
    severity_bd.adjust(5)
    severity_bd.row(cancel_seizure_menu_btn)
    severity_bd.row(confirm_seizure_data_btn)
    return severity_bd.as_markup()

def get_duration_kb() -> InlineKeyboardMarkup:
    duration_bd = InlineKeyboardBuilder()
    duration_bd.adjust(3)
    duration_btns = [
        InlineKeyboardButton(text="<1", callback_data=f"duration:<{1}"),
        InlineKeyboardButton(text="<3", callback_data=f"duration:<{3}"),
        InlineKeyboardButton(text="<5", callback_data=f"duration:<{5}"),
        InlineKeyboardButton(text="<7", callback_data=f"duration:<{7}"),
        InlineKeyboardButton(text="<10", callback_data=f"duration:<{10}"),
        InlineKeyboardButton(text="<15", callback_data=f"duration:<{15}"),
    ]
    duration_bd.row(*duration_btns)
    duration_bd.row(*[cancel_seizure_menu_btn, confirm_seizure_data_btn])
    return duration_bd.as_markup()

def generate_features_keyboard(selected_features: list, current_page: int, page_size: int = 5):
    current_page = int(current_page)
    page_size = int(page_size)
    total_pages = (len(LEXICON_EPILEPSY_TRIGGERS) + page_size - 1) // page_size
    start_index = current_page * page_size
    end_index = int(start_index) + page_size
    features_on_page = LEXICON_EPILEPSY_TRIGGERS[start_index:end_index]
    builder = InlineKeyboardBuilder()
    builder.adjust(1)
    for feature in features_on_page:
        emoji = "▫️" if feature in selected_features else "▪️"
        builder.row(InlineKeyboardButton(text=f"{emoji} {feature}", callback_data=f"toggle:{feature}:{current_page}"))
    if len(LEXICON_EPILEPSY_TRIGGERS) > page_size:
        nav_btns = []
        if current_page > 0:
            nav_btns.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{current_page-1}"))
        if current_page < total_pages - 1:
            nav_btns.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page:{current_page+1}"))
        if nav_btns:
            builder.row(*nav_btns)
    builder.row(*[cancel_seizure_menu_btn, InlineKeyboardButton(text="🗸 Готово", callback_data=f"done:{current_page}")])
    return builder.as_markup()

def get_count_of_seizures_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=f"{i}", callback_data=f"count_of_seizures:{i}")
    builder.adjust(5)
    builder.row(cancel_seizure_menu_btn)
    builder.row(confirm_seizure_data_btn)
    return builder.as_markup()