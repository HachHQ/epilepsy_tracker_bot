from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command

from database.db_init import SessionLocal
from database.models import User

from keyboards.menu_kb import get_main_menu_keyboard

from services.notification_queue import get_notification_queue

main_menu_router = Router()

# class MenuCallbackFactory(CallbackData, prefix=":"):
#     action: str
#     value: str

def get_user_login(message) -> str:
    login = ""
    db = SessionLocal()
    try:
        user_login = db.query(User).filter(User.telegram_id == message.chat.id).first()
        login = user_login.login
    finally:
        db.close()
    return login

@main_menu_router.message(Command(commands="menu"))
async def send_main_menu(message: Message):
    await message.answer(
        f"Логин: {get_user_login(message)}\n"
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard()
    )

@main_menu_router.callback_query(F.data == "to_menu")
async def send_main_menu_callback(callback: CallbackQuery):
    await callback.message.answer(
        f"Логин: {get_user_login(callback.message)}\n"
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()