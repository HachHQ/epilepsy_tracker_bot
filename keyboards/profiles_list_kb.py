from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, KeyboardButton


def get_paginated_profiles_kb(
    profiles: list,
    page: int = 0,
    page_size: int = 5,
    profile_type: str = "user_own",
    to_share: bool = False
) -> InlineKeyboardMarkup:
    total_profiles = len(profiles)
    total_pages = (total_profiles + page_size - 1) // page_size

    if page < 0 or page >= total_pages:
        page = 0

    builder = InlineKeyboardBuilder()

    start_index = page * page_size
    end_index = start_index + page_size
    for profile in profiles[start_index:end_index]:
        builder.button(
            text=profile["profile_name"],
            callback_data=f"select_profile:{profile['id']}:{profile['profile_name']}{"|share" if to_share else ""}"
        )
    builder.adjust(1)

    if total_profiles > page_size:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"prev:{page}:{profile_type}{"|share" if to_share else ""}"
                )
            )
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперед ➡️",
                    callback_data=f"next:{page}:{profile_type}{"|share" if to_share else ""}"
                )
            )
        if nav_buttons:
            builder.row(*nav_buttons)

    return builder.as_markup()

def get_choosing_type_of_profiles_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Собственные профили", callback_data="profile_type:user_own")
    builder.button(text="Профили доверенных лиц", callback_data="profile_type:trusted")
    builder.adjust(1)
    return builder.as_markup()