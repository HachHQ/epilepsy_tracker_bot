from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, KeyboardButton


def get_paginated_profils_kb(
    profiles: list,
    page: int = 0,
    page_size: int = 5,
    profile_type: str = "own"
) -> InlineKeyboardMarkup:

    total_profiles = len(profiles)
    total_pages = (total_profiles + page_size - 1) // page_size

    if page < 0 or page >= total_pages:
        page = 0

    builder = InlineKeyboardBuilder()

    # Кнопки профилей
    start_index = page * page_size
    end_index = start_index + page_size
    for profile in profiles[start_index:end_index]:
        builder.button(
            text=profile.profile_name,
            callback_data=f"select_profile:{profile.id}:{profile_type}"
        )

    # Кнопки навигации
    if total_profiles > page_size:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=PaginationFactory(
                        direction="prev",
                        page=page,
                        profile_type=profile_type
                    ).pack()
                )
            )
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперед ➡️",
                    callback_data=PaginationFactory(
                        direction="next",
                        page=page,
                        profile_type=profile_type
                    ).pack()
                )
            )
        if nav_buttons:
            builder.row(*nav_buttons)

    # Кнопка "Отмена"
    return builder.as_markup()

def get_choosing_type_of_profiles_kb() -> InlineKeyboardMarkup:
    type_of_profile_kb_bd = InlineKeyboardBuilder()
    trusted_profiles_list = InlineKeyboardButton(text="Профили доверенных лиц", callback_data="profile_type:trusted")
    user_own_profils_list = InlineKeyboardButton(text="Собственные профили", callback_data="profile_type:user_own")
    type_of_profile_kb_bd.adjust(1)
    return type_of_profile_kb_bd.as_markup()