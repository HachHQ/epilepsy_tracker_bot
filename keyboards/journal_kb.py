from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, KeyboardButton
import calendar
from datetime import datetime

dates = [datetime(2025, 3, 19), datetime(2025, 3, 29), datetime(2025, 3, 15), datetime(2025, 3, 9), datetime(2025, 1, 1), datetime(2025, 2, 1)]



def get_nav_btns_of_list_of_seizures(seizures_count, notes_on_page: int, current_page: int):
    if notes_on_page <=0:
        return
    total_pages = (seizures_count + notes_on_page - 1) // notes_on_page
    builder = InlineKeyboardBuilder()
    if seizures_count > notes_on_page:
        nav_buttons = []
        if current_page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"journal_page:{current_page - 1}"
                )
            )
        if current_page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперед ➡️",
                    callback_data=f"journal_page:{current_page + 1}"
                )
            )
        if nav_buttons:
            builder.row(*nav_buttons)
            return builder.as_markup()

    return builder.as_markup()


def get_journal_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    choose_from_year = InlineKeyboardButton(text="Выбрать год", callback_data="choose_year")
    get_graph = InlineKeyboardButton(text="Выбрать график", callback_data="choose_graph")
    last_5 = InlineKeyboardButton(text="Последние 5", callback_data="choose_last_5")
    last_10 = InlineKeyboardButton(text="Последние 10", callback_data="choose_last_10")
    last_20 = InlineKeyboardButton(text="Последние 20", callback_data="choose_last_20")
    #last_30 = InlineKeyboardButton(text="Последние 30", callback_data="choose_last_30")

def get_year_journal_kb(current_year: int, rows: int = 4) -> InlineKeyboardMarkup:
    years_journal_bd = InlineKeyboardBuilder()
    back_btn = InlineKeyboardButton(text="Назад", callback_data="years_journal_back")
    forw_btn = InlineKeyboardButton(text="Вперед", callback_data="years_journal_forw")
    years_journal_bd.adjust(rows)

    pass

def get_day_kb(year: int, month: int, dates: list[datetime], columns: int = 7) -> InlineKeyboardMarkup:
    date_set = {(date.year, date.month, date.day) for date in dates}
    kb_builder = InlineKeyboardBuilder()
    days_in_month = calendar.monthrange(year, month)[1]
    for day in range(1, days_in_month + 1):
        if (year, month, day) in date_set:
            kb_builder.button(text=f"▫️{day}", callback_data=f"day:{year}.{month}.{day}:have")
        else:
            kb_builder.button(text=str(day), callback_data=f"day:{year}.{month}.{day}")
    kb_builder.adjust(columns)
    back_btn = InlineKeyboardButton(text="Назад", callback_data="back")
    kb_builder.row(back_btn)
    return kb_builder.as_markup()