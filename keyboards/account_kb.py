from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def get_account_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Удалить аккаунт", callback_data="account_soft_delete")
    builder.button(text="Удалить все данные навсегда", callback_data="account_purge_forever")
    builder.button(text="↩️ Назад", callback_data="control_profiles")
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_soft_delete_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, удалить аккаунт", callback_data="account_soft_delete:yes")
    builder.button(text="Отмена", callback_data="account_settings")
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_purge_forever_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="ДА, УДАЛИТЬ НАВСЕГДА", callback_data="account_purge_forever:yes")
    builder.button(text="Отмена", callback_data="account_settings")
    builder.adjust(1)
    return builder.as_markup()


def get_restore_account_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Восстановить аккаунт", callback_data="account_restore_start")
    builder.adjust(1)
    return builder.as_markup()


def get_restorable_profiles_kb(profiles: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for profile in profiles:
        builder.button(
            text=f"↩️ {profile['profile_name']}",
            callback_data=f"restore_profile:{profile['id']}",
        )
    builder.button(text="↩️ Назад", callback_data="control_profiles")
    builder.adjust(1)
    return builder.as_markup()
