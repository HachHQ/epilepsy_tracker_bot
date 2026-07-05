from aiogram import Router
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import USER_DATA_RETENTION_DAYS
from keyboards.account_kb import get_restore_account_kb
from lexicon.lexicon import LEXICON_RU
from services.redis_cache_data import get_cached_login
from use_cases.users import get_deleted_account_info

start_message_router = Router()

@start_message_router.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession):
    deleted_info = await get_deleted_account_info(db, message.chat.id)
    if deleted_info and deleted_info.can_restore:
        await message.answer(
            f"Ваш аккаунт был удалён. Данные сохранены до "
            f"{deleted_info.retention_until}. Вы можете восстановить аккаунт "
            f"в течение {USER_DATA_RETENTION_DAYS} дней.",
            reply_markup=get_restore_account_kb(),
        )
        return

    if await get_cached_login(db, message.chat.id) is not None:
        await message.answer("Вы уже зарегистрированы. Используйте /menu для работы с ботом.")
        return

    welcome_kb_bd = InlineKeyboardBuilder()
    welcome_kb_bd.button(text=LEXICON_RU['to_register'], callback_data='submit_welcome_msg')
    await message.answer(LEXICON_RU['welcome'],  parse_mode='HTML')
    await message.answer(LEXICON_RU['policy'], reply_markup=welcome_kb_bd.as_markup(), parse_mode='HTML')

@start_message_router.message(Command(commands="help"))
async def help_comm(message: Message, state: FSMContext):
    text = (
        "У бота есть три основные команды:\n"
        " - /menu: присылает основное меню, через которое ведется всё взаимодействие с ботом.\n"
        " - /start: присылает привественное сообщение с руководством полльзователя.\n"
        " - /help: присылает инструкцию по пользованию ботом.\n"
        "Руководство по пользованию ботом:\n"
        ""

    )
    await message.answer(text)
