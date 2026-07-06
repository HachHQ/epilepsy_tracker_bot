from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import t


def _cancel_btn() -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t("buttons.cancel"), callback_data="cancel_fsm_script")


def get_y_or_n_buttons_to_continue_process() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data="trusted_person_correct")
    builder.button(text=t("common.no"), callback_data="add_trusted")
    builder.row(_cancel_btn())
    return builder.as_markup()


def get_y_or_n_buttons_to_finish_process() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data="confirm_transfer")
    builder.button(text=t("common.no"), callback_data="reject_transfer")
    builder.row(_cancel_btn())
    return builder.as_markup()


def get_commiting_changing_editing_permission_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data=f"tpchangeediting:yes:{tpp_id}")
    builder.button(text=t("common.no"), callback_data=f"tpchangeediting:no:{tpp_id}")
    return builder.as_markup()


def get_commiting_changing_notify_permission_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data=f"tpchangegettingnotify:yes:{tpp_id}")
    builder.button(text=t("common.no"), callback_data=f"tpchangegettingnotify:no:{tpp_id}")
    return builder.as_markup()


def get_commiting_deleting_trusted_person_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data=f"tpdeleting:yes:{tpp_id}")
    builder.button(text=t("common.no"), callback_data=f"tpdeleting:no:{tpp_id}")
    return builder.as_markup()
