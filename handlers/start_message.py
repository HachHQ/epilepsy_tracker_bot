from aiogram import Router
from aiogram.types import (
        Message, CallbackQuery,
        InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from lexicon.lexicon import LEXICON_RU

start_message_router = Router()

@start_message_router.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: Message, state: FSMContext):
    welcome_kb_bd = InlineKeyboardBuilder()
    welcome_kb_bd.button(text=LEXICON_RU['to_register'], callback_data='submit_welcome_msg')
    await message.answer(LEXICON_RU['welcome'], reply_markup=welcome_kb_bd.as_markup(), parse_mode='HTML')