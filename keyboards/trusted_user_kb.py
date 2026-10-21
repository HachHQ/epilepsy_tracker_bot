from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import t


def _cancel_btn() -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t("buttons.cancel"), callback_data="cancel_fsm_script")


def get_y_or_n_buttons_to_continue_process() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("common.yes"),
        callback_data="trusted_person_correct",
        style=ButtonStyle.SUCCESS,
    )
    builder.button(text=t("common.no"), callback_data="add_trusted")
    builder.row(_cancel_btn())
    return builder.as_markup()


def get_y_or_n_buttons_to_finish_process() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("common.yes"),
        callback_data="confirm_transfer",
        style=ButtonStyle.SUCCESS,
    )
    builder.button(text=t("common.no"), callback_data="reject_transfer")
    builder.row(_cancel_btn())
    return builder.as_markup()


def get_commiting_changing_editing_permission_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("common.yes"),
        callback_data=f"tpchangeediting:yes:{tpp_id}",
        style=ButtonStyle.SUCCESS,
    )
    builder.button(text=t("common.no"), callback_data=f"tpchangeediting:no:{tpp_id}")
    return builder.as_markup()


def get_commiting_changing_notify_permission_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("common.yes"),
        callback_data=f"tpchangegettingnotify:yes:{tpp_id}",
        style=ButtonStyle.SUCCESS,
    )
    builder.button(text=t("common.no"), callback_data=f"tpchangegettingnotify:no:{tpp_id}")
    return builder.as_markup()


def get_trusted_persons_kb(records: list[dict], *, page: int, page_size: int) -> InlineKeyboardMarkup:
    start = page * page_size
    chunk = records[start:start + page_size]
    total_pages = (len(records) + page_size - 1) // page_size if records else 1
    builder = InlineKeyboardBuilder()
    for item in chunk:
        login = item["trusted_user"]["login"]
        profile_name = item["profile"]["profile_name"]
        label = t("buttons.trusted_open_card", login=login, profile=profile_name)
        if len(label) > 60:
            label = label[:57] + "..."
        builder.button(text=label, callback_data=f"tp_card:{item['permissions']['id']}")
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text=t("buttons.back"),
            callback_data=f"trusted_person_control_panel:{page - 1}",
            style=ButtonStyle.PRIMARY,
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text=t("buttons.forward"),
            callback_data=f"trusted_person_control_panel:{page + 1}",
        ))
    if nav:
        builder.row(*nav)
    builder.adjust(1)
    return builder.as_markup()


def get_trusted_card_kb(link_id: int, *, can_edit: bool, get_notification: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("buttons.trusted_deny_edit" if can_edit else "buttons.trusted_allow_edit"),
        callback_data=f"tp_ask_edit:{link_id}",
    )
    builder.button(
        text=t("buttons.trusted_deny_notify" if get_notification else "buttons.trusted_allow_notify"),
        callback_data=f"tp_ask_notify:{link_id}",
    )
    builder.button(
        text=t("buttons.trusted_delete"),
        callback_data=f"tp_ask_delete:{link_id}",
        style=ButtonStyle.DANGER,
    )
    builder.button(
        text=t("common.back"),
        callback_data="trusted_person_control_panel",
        style=ButtonStyle.PRIMARY,
    )
    builder.adjust(1)
    return builder.as_markup()


def get_commiting_deleting_trusted_person_kb(tpp_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("common.yes"),
        callback_data=f"tpdeleting:yes:{tpp_id}",
        style=ButtonStyle.SUCCESS,
    )
    builder.button(text=t("common.no"), callback_data=f"tpdeleting:no:{tpp_id}")
    return builder.as_markup()
