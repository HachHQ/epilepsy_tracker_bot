from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from i18n import t


def get_cancel_kb() -> InlineKeyboardMarkup:
    cancel_bd = InlineKeyboardBuilder()
    cancel_bd.button(text=t("buttons.cancel"), callback_data='cancel_fsm_script')
    return cancel_bd.as_markup()
