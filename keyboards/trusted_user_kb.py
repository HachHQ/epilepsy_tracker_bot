from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton
from lexicon.lexicon import LEXICON_BUTTONS


cancel_btn = InlineKeyboardButton(text=LEXICON_BUTTONS['cancel'], callback_data="cancel_fsm_script")

def get_y_or_n_buttons_to_continue_process() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="trusted_person_correct")
    builder.button(text="Нет", callback_data="add_trusted")
    builder.row(cancel_btn)
    return builder.as_markup()

def get_y_or_n_buttons_to_finish_process() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="confirm_transfer")
    builder.button(text="Нет", callback_data="reject_transfer")
    builder.row(cancel_btn)
    return builder.as_markup()

def get_commiting_changing_editing_permission_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=f"tpchangeediting:yes:{tpp_id}")
    builder.button(text="Нет", callback_data=f"tpchangeediting:no:{tpp_id}")
    return builder.as_markup()

def get_commiting_changing_notify_permission_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=f"tpchangegettingnotify:yes:{tpp_id}")
    builder.button(text="Нет", callback_data=f"tpchangegettingnotify:no:{tpp_id}")
    return builder.as_markup()

def get_commiting_deleting_trusted_person_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=f"tpdeleting:yes:{tpp_id}")
    builder.button(text="Нет", callback_data=f"tpdeleting:no:{tpp_id}")
    return builder.as_markup()