from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton
import calendar
from datetime import datetime

def get_journal_nav_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Журнал приступов", callback_data="journal")
    builder.button(text="📉 Статистика", callback_data="stats")
    builder.button(text="📊 Графики", callback_data="graphs")
    builder.button(text="↩️ Назад", callback_data="to_menu_edit")
    builder.adjust(1)
    return builder.as_markup()

def get_nav_btns_for_list(seizures_count, notes_on_page: int, current_page: int, prefix: str):
    current_page = int(current_page)
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
                    callback_data=f"{prefix}:{current_page - 1}"
                )
            )
        if current_page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперед ➡️",
                    callback_data=f"{prefix}:{current_page + 1}"
                )
            )
        if nav_buttons:
            builder.row(*nav_buttons)
            return builder.as_markup()

    return builder.as_markup()

def get_delete_edit_kb(seizure_id):
    builder = InlineKeyboardBuilder()
    delete_btn = InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete|{seizure_id}")
    edit_btn = InlineKeyboardButton(text="✍️ Изменить", callback_data=f"edit|{seizure_id}")
    builder.button(delete_btn)
    builder.button(edit_btn)
    builder.adjust(2)
    return builder.as_markup()


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

def get_delete_seizure_note_kb(seizure_id: int):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Да", callback_data=f"delete_seizure_note:yes:{seizure_id}")
    kb_builder.button(text="Нет", callback_data=f"delete_seizure_note:no")
    return kb_builder.as_markup()