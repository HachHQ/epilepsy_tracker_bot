from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import SEIZURE_RETENTION_DAYS, USER_DATA_RETENTION_DAYS
from handlers_logic.states_factories import AccountForm
from i18n import t
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
        t("account.settings", user_retention_days=USER_DATA_RETENTION_DAYS),
        reply_markup=get_account_settings_kb(),
    )
    await callback.answer()


@account_router.callback_query(F.data == "account_soft_delete")
async def confirm_soft_delete(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        t("account.soft_delete_confirm", days=USER_DATA_RETENTION_DAYS),
        reply_markup=get_confirm_soft_delete_kb(),
    )
    await callback.answer()


@account_router.callback_query(F.data == "account_soft_delete:yes")
async def process_soft_delete(callback: CallbackQuery, db: AsyncSession) -> None:
    result = await soft_delete_account(db, chat_id=callback.message.chat.id)
    if result.deleted:
        await callback.message.edit_text(
            t("account.soft_delete_success", days=result.retention_days)
        )
    else:
        await callback.message.edit_text(t("account.soft_delete_failed"))
    await callback.answer()


@account_router.callback_query(F.data == "account_purge_forever")
async def confirm_purge_forever(callback: CallbackQuery, state: FSMContext) -> None:
    phrase = t("account.purge_phrase")
    await callback.message.edit_text(
        t("account.purge_confirm", phrase=phrase),
        reply_markup=get_confirm_purge_forever_kb(),
    )
    await state.set_state(AccountForm.confirm_purge_forever)
    await callback.answer()


@account_router.callback_query(F.data == "account_purge_forever:yes")
async def process_purge_forever_button(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        t("account.purge_prompt", phrase=t("account.purge_phrase")),
        reply_markup=get_cancel_kb(),
    )
    await state.set_state(AccountForm.confirm_purge_forever)
    await callback.answer()


@account_router.message(StateFilter(AccountForm.confirm_purge_forever))
async def process_purge_forever_text(message: Message, state: FSMContext, db: AsyncSession) -> None:
    if message.text != t("account.purge_phrase"):
        await message.answer(t("account.purge_mismatch"))
        await state.clear()
        return

    result = await purge_account_forever(db, chat_id=message.chat.id)
    await state.clear()
    if result.purged:
        await message.answer(t("account.purge_success"))
    else:
        await message.answer(t("account.purge_failed"))


@account_router.callback_query(F.data == "prof_restore_list")
async def list_restorable_profiles_handler(callback: CallbackQuery, db: AsyncSession) -> None:
    profiles = await list_restorable_profile_records(db, callback.message.chat.id)
    if not profiles:
        await callback.message.edit_text(
            t("account.restore_list_empty", days=SEIZURE_RETENTION_DAYS),
            reply_markup=get_account_settings_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        t("account.restore_list_prompt"),
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
            t("account.restore_profile_success", profile_name=result.profile_name)
        )
    else:
        await callback.message.edit_text(t("account.restore_profile_failed"))
    await callback.answer()


@account_router.callback_query(F.data.startswith("purge_profile_forever:"))
async def purge_profile_forever_handler(callback: CallbackQuery, db: AsyncSession) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    result = await purge_profile_forever_record(
        db, chat_id=callback.message.chat.id, profile_id=profile_id,
    )
    if result.purged:
        await callback.message.edit_text(t("account.purge_profile_success"))
    else:
        await callback.message.edit_text(t("account.purge_profile_failed"))
    await callback.answer()


@account_router.callback_query(F.data == "account_restore_start")
async def start_account_restore(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        t("account.restore_codeword_prompt"),
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
            t("account.restore_codeword_invalid"),
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
            t("account.restore_success", profiles_restored=result.profiles_restored)
        )
    else:
        await message.answer(t("account.restore_failed"))
