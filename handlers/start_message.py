from aiogram import Router
from aiogram.types import (
        Message, CallbackQuery,
        InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

start_message_router = Router()

@start_message_router.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: Message, state: FSMContext):
    welcome_text = (
        "Привет! Я бот для управления данными о профилях, связанных с эпилепсией.\n\n"
        "Доступные возможности:\n"
        "__Скоро заполню__\n"
        "Нажмите на кнопку для перехода к заполнению анкеты пользователя"
    )
    welcome_kb_bd =  InlineKeyboardBuilder()
    welcome_kb_bd.button(text="К заполнению анкеты", callback_data='submit_welcome_msg')
    # next_text = ("Для продолжения необходимо заполнить анкету. Введите свое имя:")
    await message.answer(welcome_text, reply_markup=welcome_kb_bd.as_markup())
    #await message.answer(next_text)
    #await state.set_state(UserForm.name)
