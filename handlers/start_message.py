from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.anchor import live_message, send_anchor
from adapters.telegram.oferta import send_oferta_document
from config_data.retention import USER_DATA_RETENTION_DAYS
from handlers_logic.states_factories import UserForm
from i18n import t
from keyboards.account_kb import get_restore_account_kb
from keyboards.menu_kb import get_cancel_kb
from use_cases.users import accept_oferta, get_deleted_account_info, get_oferta_account_state

start_message_router = Router()


async def _send_deleted_account(message: Message, db: AsyncSession, chat_id: int) -> None:
    deleted_info = await get_deleted_account_info(db, chat_id)
    if deleted_info and deleted_info.can_restore:
        await message.answer(
            t(
                "start.deleted_account",
                retention_until=deleted_info.retention_until,
                days=USER_DATA_RETENTION_DAYS,
            ),
            reply_markup=get_restore_account_kb(),
        )
        return
    await message.answer(t("account.restore_failed"))


@start_message_router.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: Message, db: AsyncSession):
    account = await get_oferta_account_state(db, message.chat.id)
    if account.exists and account.is_oferta_accepted and account.is_deleted:
        await _send_deleted_account(message, db, message.chat.id)
        return

    if account.exists and account.is_oferta_accepted:
        await message.answer(t("start.already_registered"))
        await _send_oferta(message, with_accept_button=False)
        return

    if not account.exists:
        await message.answer(t("start.welcome"), parse_mode="HTML")
    elif account.is_deleted:
        await message.answer(t("start.oferta_before_restore"))

    await _send_oferta(message, with_accept_button=True)


async def _send_oferta(message: Message, *, with_accept_button: bool) -> None:
    if message.bot is None:
        return
    await send_oferta_document(message.bot, message.chat.id, with_accept_button=with_accept_button)


@start_message_router.callback_query(F.data == "accept_oferta")
async def accept_oferta_handler(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    chat_id = message.chat.id if message is not None else callback.from_user.id
    account = await get_oferta_account_state(db, chat_id)
    if account.exists:
        await accept_oferta(db, chat_id=chat_id)
        await callback.answer(t("start.oferta_accepted_alert"))
        if message is None:
            return
        if account.is_deleted:
            await _send_deleted_account(message, db, chat_id)
            return
        await message.answer(t("start.oferta_accepted_registered"))
        return

    if message is None:
        await callback.answer()
        return
    await state.update_data(oferta_accepted=True)
    await send_anchor(message, state, t("user.enter_username"), reply_markup=get_cancel_kb())
    await state.set_state(UserForm.name)
    await callback.answer()


@start_message_router.message(Command(commands="help"))
async def help_comm(message: Message, state: FSMContext):
    await message.answer(t("start.help"))
