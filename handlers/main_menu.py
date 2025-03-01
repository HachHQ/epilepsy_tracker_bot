from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.db_init import SessionLocal
from database.models import User
from database.redis_client import redis

from services.notification_queue import NotificationQueue

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
        async with SessionLocal() as db:
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
async def send_notification_someone(message: Message, notification_queue: NotificationQueue, db: AsyncSession):
    try:
        login = message.text.split("_", 1)[1]  # Разделяем 'send_логин' → получаем логин
        print(f"Поиск пользователя с логином: {login}")

        result = await db.execute(select(User).filter(User.login == login))
        user = result.scalars().first()
        if not user:
            print("Пользователь не найден")
            await message.answer("Пользователь не найден.")
            return

        print(f"Найден пользователь: {user.telegram_id}")
        await notification_queue.send_notification(user.telegram_id, "Уведомление")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")

# @main_menu_router.message(F.text.startswith('send_'))
# async def send_trusted_request(message: Message, db: Session, notification_queue: NotificationQueue):
#     sender = db.query(User).filter(User.telegram_id == message.from_user.id).first()
#     if not sender:
#         await message.answer("Ваш аккаунт не найден в системе.")
#         return

#     receiver_login = message.text.split("_", 1)[1]
#     receiver = db.query(User).filter(User.login == receiver_login).first()
#     if not receiver:
#         await message.answer("Пользователь не найден.")
#         return

#     request = TrustedRequest(sender_id=sender.id, receiver_id=receiver.id)
#     db.add(request)
#     db.commit()

#     await notification_queue.send_notification(
#         receiver.telegram_id,
#         f"{sender.name} хочет добавить вас в доверенные лица. Принять запрос?",
#         request_id=request.id
#     )

#     await message.answer("Запрос отправлен!")
