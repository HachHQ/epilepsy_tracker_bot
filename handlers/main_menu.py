from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command

from database.db_init import SessionLocal
from database.models import User
from database.redis_client import redis

from keyboards.menu_kb import get_main_menu_keyboard

# from services.notification_queue import get_notification_queue

main_menu_router = Router()

# class MenuCallbackFactory(CallbackData, prefix=":"):
#     action: str
#     value: str

async def get_user_login(message) -> str:
    user_id = message.chat.id
    login = None
    # Пытаемся получить логин из Redis
    login_bytes = await redis.get(f"user:login:{user_id}")
    print(login_bytes)
    if login_bytes:
        login = login_bytes.decode('utf-8')
    print(login)
    if not login:
        # Если нет в кэше, достаем из БД
        db = SessionLocal()
        user = db.query(User).filter(User.telegram_id == user_id).first()
        db.close()

        if user:
            login = user.login
            await redis.setex(f"user:login:{user_id}", 300, login)  # Сохраняем в кэше

    return login or "Логин не найден"

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

@main_menu_router.message(F.text.startswith('send_'))
async def send_notification_someone(message: Message, notification_queue):
    db = SessionLocal()
    try:
        login = message.text.split("_", 1)[1]  # Разделяем 'send_логин' → получаем логин
        print(f"Поиск пользователя с логином: {login}")

        user = db.query(User).filter(User.login == login).first()
        if not user:
            print("Пользователь не найден")
            await message.answer("Пользователь не найден.")
            return

        print(f"Найден пользователь: {user.telegram_id}")
        await notification_queue.send_notification(user.telegram_id, "Уведомление")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
    finally:
        db.close()
