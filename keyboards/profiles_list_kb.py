from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton

from i18n import t


def get_paginated_profiles_kb(
    profiles: list,
    page: int = 0,
    page_size: int = 5,
    profile_type: str = "user_own",
    to_share: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if profiles is None:
        builder.button(text=t("buttons.create_profile"), callback_data="to_filling_profile_form")
        return builder.as_markup()
    total_profiles = len(profiles)
    total_pages = (total_profiles + page_size - 1) // page_size
    if page < 0 or page >= total_pages:
        page = 0
    start_index = page * page_size
    end_index = start_index + page_size
    builder.button(text=t("buttons.create_profile"), callback_data="to_filling_profile_form")
    for index, profile in enumerate(profiles[start_index:end_index]):
        builder.button(text=f"{index+1} - " + profile["profile_name"],callback_data=f"select_profile:{profile['id']}:{profile['profile_name']}{"|share" if to_share else ""}")
    builder.adjust(1)
    if total_profiles > page_size:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text=t("buttons.back"), callback_data=f"prev:{page}:{profile_type}{"|share" if to_share else ""}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text=t("buttons.forward"), callback_data=f"next:{page}:{profile_type}{"|share" if to_share else ""}"))
        if nav_buttons:
            builder.row(*nav_buttons)
    return builder.as_markup()

def get_choosing_type_of_profiles_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.own_profiles"), callback_data="profile_type:user_own")
    builder.button(text=t("buttons.trusted_profiles"), callback_data="profile_type:trusted")
    builder.adjust(1)
    return builder.as_markup()

def get_profile_submenu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.edit_profile"), callback_data="prof_edit")
    builder.button(text=t("buttons.trusted_panel"), callback_data="trusted_person_control_panel")
    builder.button(text=t("buttons.add_trusted"), callback_data="add_trusted")
    builder.button(text=t("buttons.import_data"), callback_data="import_data")
    builder.button(text=t("buttons.export_data"), callback_data="export_data")
    builder.button(text=t("buttons.restore_profile"), callback_data="prof_restore_list")
    builder.button(text=t("buttons.account"), callback_data="account_settings")
    builder.button(text=t("common.back"), callback_data="to_menu_edit")
    builder.adjust(1)
    return builder.as_markup()
