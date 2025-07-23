from aiogram import Router
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.filters import Command

from lexicon.lexicon import LEXICON_RU

start_message_router = Router()

@start_message_router.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: Message, state: FSMContext):
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
