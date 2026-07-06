import calendar
from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import t


def get_journal_nav_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.journal_list"), callback_data="journal")
    builder.button(text=t("buttons.stats"), callback_data="stats")
    builder.button(text=t("buttons.graphs"), callback_data="graphs")
    builder.button(text=t("common.back"), callback_data="to_menu_edit")
    builder.adjust(1)
    return builder.as_markup()


def get_graphs_type():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.graph_duration"), callback_data="duration_graphs")
    builder.button(text=t("buttons.graph_frequency"), callback_data="frequency_graphs")
    builder.button(text=t("buttons.graph_efficiency"), callback_data="efficiency_graphs")
    builder.button(text=t("common.back"), callback_data="seizure_data")
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
                    text=t("buttons.back"),
                    callback_data=f"{prefix}:{current_page - 1}"
                )
            )
        if current_page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text=t("buttons.forward"),
                    callback_data=f"{prefix}:{current_page + 1}"
                )
            )
        if nav_buttons:
            builder.row(*nav_buttons)
            return builder.as_markup()

    return builder.as_markup()


def get_delete_edit_kb(seizure_id):
    builder = InlineKeyboardBuilder()
    delete_btn = InlineKeyboardButton(text=t("buttons.delete_item"), callback_data=f"delete|{seizure_id}")
    edit_btn = InlineKeyboardButton(text=t("buttons.edit_item"), callback_data=f"edit|{seizure_id}")
    builder.button(delete_btn)
    builder.button(edit_btn)
    builder.adjust(2)
    return builder.as_markup()


def get_year_journal_kb(current_year: int, rows: int = 4) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.adjust(rows)
    return builder.as_markup()

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
    back_btn = InlineKeyboardButton(text=t("buttons.back_plain"), callback_data="back")
    kb_builder.row(back_btn)
    return kb_builder.as_markup()


def get_delete_seizure_note_kb(seizure_id: int):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text=t("common.yes"), callback_data=f"delete_seizure_note:yes:{seizure_id}")
    kb_builder.button(text=t("common.no"), callback_data="delete_seizure_note:no")
    return kb_builder.as_markup()
