from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import t


def get_cancel_kb() -> InlineKeyboardMarkup:
    cancel_bd = InlineKeyboardBuilder()
    cancel_bd.button(text=t("buttons.cancel"), callback_data='cancel_fsm_script')
    return cancel_bd.as_markup()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(
            text=t("menu.main_sos"),
            callback_data="sos_notification",
            style=ButtonStyle.DANGER,
        ),
    )
    kb_builder.row(
        InlineKeyboardButton(text=t("menu.main_seizure_now"), callback_data="seizure_right_now"),
    )
    kb_builder.row(
        InlineKeyboardButton(text=t("menu.main_seizure_passed"), callback_data="seizure_passed"),
    )
    kb_builder.row(
        InlineKeyboardButton(text=t("menu.main_choose_profile"), callback_data="choose_profile"),
        InlineKeyboardButton(text=t("menu.main_notifications"), callback_data="notifications_control"),
    )
    kb_builder.row(
        InlineKeyboardButton(text=t("menu.main_journal"), callback_data="seizure_data"),
    )
    kb_builder.row(
        InlineKeyboardButton(text=t("menu.main_control"), callback_data="control_profiles"),
        InlineKeyboardButton(text=t("menu.main_medication"), callback_data="medication"),
    )
    return kb_builder.as_markup()
