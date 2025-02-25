from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command

from database.db_init import SessionLocal
from database.models import User
from database.redis_client import redis

from keyboards.menu_kb import get_main_menu_keyboard

from services.notification_queue import get_notification_queue

main_menu_router = Router()

# class MenuCallbackFactory(CallbackData, prefix=":"):
#     action: str
#     value: str

async def get_user_login(message) -> str:
    user_id = message.chat.id

    # Пытаемся получить логин из Redis
    login = await redis.get(f"user:login:{user_id}")

    if not login:
        # Если нет в кэше, достаем из БД
        db = SessionLocal()
        user = db.query(User).filter(User.telegram_id == user_id).first()
        db.close()

        if user:
            login = user.login
            await redis.setex(f"user:login:{user_id}", 300, login)  # Сохраняем в кэше

    return login

@main_menu_router.message(Command(commands="menu"))
async def send_main_menu(message: Message):
    await message.answer(
        f"Логин: {await get_user_login(message)}\n"
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard()
    )

@main_menu_router.callback_query(F.data == "to_menu")
async def send_main_menu_callback(callback: CallbackQuery):
    await callback.message.answer(
        f"Логин: {await get_user_login(callback.message)}\n"
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()