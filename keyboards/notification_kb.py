from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, KeyboardButton

from i18n import t


def get_cancel_kb() -> InlineKeyboardMarkup:
    cancel_bd = InlineKeyboardBuilder()
    cancel_bd.button(text=t("buttons.cancel"), callback_data='cancel_fsm_script')
    return cancel_bd.as_markup()


def get_notify_sumbenu():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.add_notification"), callback_data="add_notification")
    builder.button(text=t("buttons.manage"), callback_data="notification_control_panel")
    builder.button(text=t("common.back"), callback_data="to_menu_edit")
    builder.adjust(1)
    return builder.as_markup()


def get_notify_pattern():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.pattern_daily"), callback_data="notification_pattern:daily")
    builder.button(text=t("buttons.pattern_once"), callback_data="notification_pattern:once")
    builder.adjust(1)
    return builder.as_markup()


def get_notify_to_enable_kb(nt_id, user_id, enabled_mode: bool):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data=f"nt_enabled_mode:yes:{nt_id}:{user_id}:{enabled_mode}")
    builder.button(text=t("common.no"), callback_data=f"nt_enabled_mode:no:{nt_id}:{user_id}:{enabled_mode}")
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_deleting_notify_kb(nt_id, user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data=f"nt_delete:yes:{nt_id}:{user_id}")
    builder.button(text=t("common.no"), callback_data=f"nt_enabled_mode:no:{nt_id}:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_choose_sos_notify_mode_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.send_notifications"), callback_data="sos_notify_with_geo:yes")
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_of_notification_message():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data="confirm_getting_notification")
    builder.adjust(1)
    return builder.as_markup()
