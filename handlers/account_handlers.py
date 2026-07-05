from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import SEIZURE_RETENTION_DAYS, USER_DATA_RETENTION_DAYS
from handlers_logic.states_factories import AccountForm
from keyboards.account_kb import (
    get_account_settings_kb,
    get_confirm_purge_forever_kb,
    get_confirm_soft_delete_kb,
    get_restorable_profiles_kb,
)
from keyboards.menu_kb import get_cancel_kb
from services.keyword_hasher import KeywordHasher
from services.validators import validate_codeword
from use_cases.profiles import (
    list_restorable_profile_records,
    purge_profile_forever_record,
    restore_profile_record,
)
from use_cases.users import (
    purge_account_forever,
    restore_account,
    soft_delete_account,
)

account_router = Router()


@account_router.callback_query(F.data == "account_settings")
async def show_account_settings(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Управление аккаунтом:\n\n"
        f"• «Удалить аккаунт» — скрывает данные на {USER_DATA_RETENTION_DAYS} дней, "
        "после чего их можно восстановить через /start.\n"
        "• «Удалить все данные навсегда» — безвозвратное удаление профилей, "
        "приступов и аккаунта.",
        reply_markup=get_account_settings_kb(),
    )
    await callback.answer()


@account_router.callback_query(F.data == "account_soft_delete")
async def confirm_soft_delete(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        f"Аккаунт будет скрыт на {USER_DATA_RETENTION_DAYS} дней. "
        "Профили будут помечены удалёнными, записи о приступах сохранятся. "
        "Вы сможете восстановить аккаунт через /start.\n\nПродолжить?",
        reply_markup=get_confirm_soft_delete_kb(),
    )
    await callback.answer()


@account_router.callback_query(F.data == "account_soft_delete:yes")
async def process_soft_delete(callback: CallbackQuery, db: AsyncSession) -> None:
    result = await soft_delete_account(db, chat_id=callback.message.chat.id)
    if result.deleted:
        await callback.message.edit_text(
            f"Аккаунт удалён. Данные сохранены {result.retention_days} дней. "
            "Для восстановления нажмите /start."
        )
    else:
        await callback.message.edit_text("Не удалось удалить аккаунт.")
    await callback.answer()


@account_router.callback_query(F.data == "account_purge_forever")
async def confirm_purge_forever(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Это действие необратимо: все профили, приступы и данные аккаунта "
        "будут удалены без возможности восстановления.\n\n"
        "Отправьте сообщение «УДАЛИТЬ НАВСЕГДА» для подтверждения.",
        reply_markup=get_confirm_purge_forever_kb(),
    )
    await state.set_state(AccountForm.confirm_purge_forever)
    await callback.answer()


@account_router.callback_query(F.data == "account_purge_forever:yes")
async def process_purge_forever_button(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "Отправьте сообщение «УДАЛИТЬ НАВСЕГДА» для подтверждения.",
        reply_markup=get_cancel_kb(),
    )
    await state.set_state(AccountForm.confirm_purge_forever)
    await callback.answer()


@account_router.message(StateFilter(AccountForm.confirm_purge_forever))
async def process_purge_forever_text(message: Message, state: FSMContext, db: AsyncSession) -> None:
    if message.text != "УДАЛИТЬ НАВСЕГДА":
        await message.answer("Подтверждение не совпало. Операция отменена.")
        await state.clear()
        return

    result = await purge_account_forever(db, chat_id=message.chat.id)
    await state.clear()
    if result.purged:
        await message.answer("Все данные аккаунта безвозвратно удалены.")
    else:
        await message.answer("Не удалось удалить данные аккаунта.")


@account_router.callback_query(F.data == "prof_restore_list")
async def list_restorable_profiles_handler(callback: CallbackQuery, db: AsyncSession) -> None:
    profiles = await list_restorable_profile_records(db, callback.message.chat.id)
    if not profiles:
        await callback.message.edit_text(
            f"Нет профилей для восстановления. Удалённые профили доступны "
            f"{SEIZURE_RETENTION_DAYS} дней после удаления.",
            reply_markup=get_account_settings_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите профиль для восстановления:",
        reply_markup=get_restorable_profiles_kb(profiles),
    )
    await callback.answer()


@account_router.callback_query(F.data.startswith("restore_profile:"))
async def restore_profile_handler(callback: CallbackQuery, db: AsyncSession) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    result = await restore_profile_record(
        db, chat_id=callback.message.chat.id, profile_id=profile_id,
    )
    if result.restored:
        await callback.message.edit_text(
            f"Профиль «{result.profile_name}» восстановлен."
        )
    else:
        await callback.message.edit_text(
            "Не удалось восстановить профиль. Возможно, истёк срок хранения."
        )
    await callback.answer()


@account_router.callback_query(F.data.startswith("purge_profile_forever:"))
async def purge_profile_forever_handler(callback: CallbackQuery, db: AsyncSession) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    result = await purge_profile_forever_record(
        db, chat_id=callback.message.chat.id, profile_id=profile_id,
    )
    if result.purged:
        await callback.message.edit_text("Профиль и все связанные данные удалены навсегда.")
    else:
        await callback.message.edit_text("Не удалось удалить профиль.")
    await callback.answer()


@account_router.callback_query(F.data == "account_restore_start")
async def start_account_restore(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "Введите новое ключевое слово для восстановления аккаунта "
        "(от 8 до 25 символов):",
        reply_markup=get_cancel_kb(),
    )
    await state.set_state(AccountForm.restore_codeword)
    await callback.answer()


@account_router.message(StateFilter(AccountForm.restore_codeword))
async def process_restore_codeword(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    if not validate_codeword(message.text):
        await message.answer(
            "Ключевое слово должно быть от 8 до 25 символов.",
            reply_markup=get_cancel_kb(),
        )
        return

    hasher = KeywordHasher()
    result = await restore_account(
        db,
        chat_id=message.chat.id,
        telegram_username=message.from_user.username,
        telegram_fullname=message.from_user.full_name,
        keyword_hash=hasher.hash_keyword(message.text),
    )
    await state.clear()
    if result.restored:
        await message.answer(
            f"Аккаунт восстановлен. Восстановлено профилей: {result.profiles_restored}."
        )
    else:
        await message.answer("Не удалось восстановить аккаунт. Возможно, истёк срок хранения.")
