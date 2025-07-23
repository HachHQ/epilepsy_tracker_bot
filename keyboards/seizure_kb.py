import calendar
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timezone, timedelta

from services.redis_cache_data import get_user_local_datetime
from lexicon.lexicon import LEXICON_EPILEPSY_TRIGGERS, LEXICON_TYPES_OF_SEIZURE
cancel_seizure_menu_btn = InlineKeyboardButton(text="❌", callback_data="cancel_fsm_script")
confirm_seizure_data_btn = InlineKeyboardButton(text="✅", callback_data="check_input_seizure_data")
skip_btn = InlineKeyboardButton(text="⏩", callback_data="skip_step")
main_btns = [cancel_seizure_menu_btn, confirm_seizure_data_btn, skip_btn]

final_seizure_bts = [
    InlineKeyboardButton(text="Отменить заполнение", callback_data="cancel_fsm_script"),
    InlineKeyboardButton(text="Завершить заполнение", callback_data="check_input_seizure_data")
]

def get_final_seizure_btns():
    builder = InlineKeyboardBuilder()
    builder.adjust(1)
    builder.row(*final_seizure_bts)
    return builder.as_markup()

def get_temporary_cancel_submit_kb(action_btns: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if action_btns:
        builder.row(*main_btns)
        return builder.as_markup()
    else:
        pass

def get_year_date_kb(backward_offset: int = 3, forward_offset: int = 1, action_btns: bool = True):
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
    if action_btns:
        years_date_kb_bd.row(cancel_seizure_menu_btn)
    return years_date_kb_bd.as_markup()

def get_month_date_kb(action_btns: bool = True) -> InlineKeyboardMarkup:
    month_kb_bd = InlineKeyboardBuilder()
    month_in_russian = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    for i in range(1, 13):
        month_kb_bd.button(text=month_in_russian[i-1], callback_data=f"month:{i}:{month_in_russian[i-1]}")
    month_kb_bd.adjust(3)
    if action_btns:
        month_kb_bd.row(cancel_seizure_menu_btn)
    return month_kb_bd.as_markup()

def get_day_kb(year: int, month: int, action_btns: bool = True) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    days_in_month = calendar.monthrange(year, month)[1]
    for day in range(1, days_in_month + 1):
        kb_builder.button(text=str(day), callback_data=f"day:{day}")
    kb_builder.adjust(7)
    print(action_btns)
    if action_btns:
        kb_builder.row(cancel_seizure_menu_btn)
    return kb_builder.as_markup()

def get_time_ranges_kb(action_btns: bool = True) -> InlineKeyboardMarkup:
    time_ranges = {
        '2 часа назад':'2h_ago',
        '1.5 часа назад':'1p5h_ago',
        '1 час назад':'1h_ago',
        '30 мин назад':'30m_ago',
        '15 мин назад':'15m_ago',
        '5 мин назад':'5m_ago',
        'Сейчас':'now'
    }
    builder = InlineKeyboardBuilder()
    for key, value in time_ranges.items():
        builder.button(text=f"{key}", callback_data=f"time_range:{value}")
    builder.adjust(3)
    if action_btns:
        builder.row(*main_btns)
    return builder.as_markup()

def get_severity_kb(action_btns: bool = True) -> InlineKeyboardMarkup:
    severity_bd = InlineKeyboardBuilder()
    for i in range(1, 11):
        severity_bd.button(text=f"{i}", callback_data=f"saverity:{i}")
    severity_bd.adjust(5)
    if action_btns:
        severity_bd.row(*main_btns)
    return severity_bd.as_markup()

def get_duration_kb(action_btns: bool = True) -> InlineKeyboardMarkup:
    duration_bd = InlineKeyboardBuilder()
    duration_btns = [
        InlineKeyboardButton(text="< 30 сек", callback_data=f"seizure_duration:<-{30}-s"),
        InlineKeyboardButton(text="< 1 мин", callback_data=f"seizure_duration:<-{60}-s"),
        InlineKeyboardButton(text="1 - 2 мин", callback_data=f"seizure_duration:<-{90}-s"),
        InlineKeyboardButton(text="2 - 5 мин", callback_data=f"seizure_duration:<-{200}-s"),
        InlineKeyboardButton(text="Более 5 мин", callback_data=f"seizure_duration:>-{300}-s"),
    ]
    duration_bd.row(*duration_btns)
    duration_bd.adjust(3)
    if action_btns:
        duration_bd.row(*main_btns)
    return duration_bd.as_markup()

def generate_features_keyboard(features_list: list, selected_features: list, current_page: int, page_size: int = 5, action_btns: bool = True):
    current_page = int(current_page)
    page_size = int(page_size)
    total_pages = (len(features_list) + page_size - 1) // page_size
    start_index = current_page * page_size
    end_index = int(start_index) + page_size
    features_on_page = features_list[start_index:end_index]
    builder = InlineKeyboardBuilder()
    builder.adjust(1)
    for feature in features_on_page:
        emoji = "▫️" if feature in selected_features else "▪️"
        builder.row(InlineKeyboardButton(text=f"{emoji} {feature}", callback_data=f"toggle:{feature}:{current_page}"))
    if len(features_list) > page_size:
        nav_btns = []
        if current_page > 0:
            nav_btns.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{current_page-1}"))
        if current_page < total_pages - 1:
            nav_btns.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page:{current_page+1}"))
        if nav_btns:
            builder.row(*nav_btns)
    if action_btns:
        builder.row(*[InlineKeyboardButton(text="☑️ Готово", callback_data=f"done:{current_page}")])
        builder.row(*main_btns)
    else:
        builder.row(InlineKeyboardButton(text="☑️ Готово", callback_data=f"done:{current_page}"))
    return builder.as_markup()

def generate_seizure_type_keyboard(current_page: int, page_size: int = 5, action_btns: bool = True) -> InlineKeyboardMarkup:
    current_page = int(current_page)
    page_size = int(page_size)
    builder = InlineKeyboardBuilder()
    total_items = list(LEXICON_TYPES_OF_SEIZURE.items())
    total_pages = (len(total_items) + page_size - 1) // page_size
    start_index = current_page * page_size
    end_index = start_index + page_size
    features_on_page = total_items[start_index:end_index]
    for index, label in features_on_page:
        builder.button(
            text=label,
            callback_data=f"seizure_type:{index}"
        )
    builder.adjust(1)
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"seizure_type_page:{current_page - 1}"
        ))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"seizure_type_page:{current_page + 1}"
        ))
    if nav_buttons:
        builder.row(*nav_buttons)
    if action_btns:
        builder.row(*main_btns)
    return builder.as_markup()

def get_count_of_seizures_kb(action_btns: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=f"{i}", callback_data=f"count_of_seizures:{i}")
    builder.adjust(5)
    if action_btns:
        builder.row(*main_btns)
    return builder.as_markup()

def get_seizure_timing():
    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ Приступ происходит сейчас", callback_data="seizure_right_now")
    builder.button(text="🕓 Приступ уже прошёл", callback_data="seizure_passed")
    builder.button(text="↩️ Назад", callback_data="to_menu_edit")
    builder.adjust(1)
    return builder.as_markup()

def get_stop_duration_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔴 Стоп", callback_data="stop_track_duration")
    builder.row(*[cancel_seizure_menu_btn, confirm_seizure_data_btn])
    return builder.as_markup()

def build_statistics_navigation_keyboard(current_page: str = "stats") -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    if current_page != "stats":
        kb.button(text="📊 Статистика", callback_data="stats_edit")
    if current_page != "features":
        kb.button(text="🧾 Частые признаки", callback_data="view:features")
    kb.adjust(1)
    return kb.as_markup()