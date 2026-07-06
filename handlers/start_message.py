from aiogram import Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import USER_DATA_RETENTION_DAYS
from i18n import t
from keyboards.account_kb import get_restore_account_kb
from services.redis_cache_data import get_cached_login
from use_cases.users import get_deleted_account_info

start_message_router = Router()

@start_message_router.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession):
    deleted_info = await get_deleted_account_info(db, message.chat.id)
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

    if await get_cached_login(db, message.chat.id) is not None:
        await message.answer(t("start.already_registered"))
        return

    welcome_kb_bd = InlineKeyboardBuilder()
    welcome_kb_bd.button(text=t("start.to_register"), callback_data='submit_welcome_msg')
    await message.answer(t("start.welcome"), parse_mode='HTML')
    await message.answer(t("start.policy"), reply_markup=welcome_kb_bd.as_markup(), parse_mode='HTML')

@start_message_router.message(Command(commands="help"))
async def help_comm(message: Message, state: FSMContext):
    await message.answer(t("start.help"))
