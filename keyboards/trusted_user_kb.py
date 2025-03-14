from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, KeyboardButton
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