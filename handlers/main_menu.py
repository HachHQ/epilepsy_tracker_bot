from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.models import User, TrustedPersonRequest
from database.redis_client import redis
from services.notification_queue import NotificationQueue
from services.update_login_cache import get_cached_login, set_cached_login
from keyboards.menu_kb import get_main_menu_keyboard

main_menu_router = Router()

# class MenuCallbackFactory(CallbackData, prefix=":"):
#     action: str
#     value: str

# async def get_user_login(message) -> str:
#     user_id = message.chat.id
#     login = None
#     login_bytes = await redis.get(f"user:login:{user_id}")
#     print(login_bytes)
#     if login_bytes:
#         login = login_bytes.decode('utf-8')
#     print(login)
#     if not login:
#         async with SessionLocal() as db:
#             user = db.query(User).filter(User.telegram_id == user_id).first()

#             if user:
#                 login = user.login
#                 await redis.setex(f"user:login:{user_id}", 300, login)

#     return login or "Логин не найден"

@main_menu_router.message(Command(commands="menu"))
async def send_main_menu(message: Message, db: AsyncSession):
    lg = await get_cached_login(message.chat.id)
    print(lg)
    await message.answer(
        f"Логин: {lg}\n"
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard()
    )

@main_menu_router.callback_query(F.data == "to_menu")
async def send_main_menu_callback(callback: CallbackQuery, db: AsyncSession):
    result = await db.execute(select(User).filter(User.login == callback.message.chat.id))
    user_login = result.scalars().first()
    print(user_login)
    set_cached_login(callback.message.chat.id, user_login)
    await callback.message.answer(
        f"Логин: {get_cached_login()}\n"
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@main_menu_router.message(F.text.startswith('send_'))
async def send_notification_someone(message: Message, notification_queue: NotificationQueue, db: AsyncSession):
    try:
        recipient_login = message.text.split("_", 1)[1]
        sender_login = await get_cached_login(message.chat.id)

        print(f"Поиск пользователя с логином: {recipient_login}")
        search_user_result = await db.execute(select(User).filter(User.telegram_id == message.chat.id))
        user = search_user_result.scalars().first()
        search_recipient_result = await db.execute(select(User).filter(User.login == recipient_login))
        recipient = search_recipient_result.scalars().first()

        if not recipient:
            print("Пользователь не найден")
            await message.answer("Пользователь не найден.")
            return
        print(f"Найден пользователь: {recipient.login} - {recipient.telegram_id}")

        

        new_request = TrustedPersonRequest(
            user_id = user.id,
            recipient_id = recipient.id
        )

        print(f"Новый запрос добавлен: {new_request}")
        await notification_queue.send_trusted_contact_request(recipient.telegram_id,  request_uuid=new_request.request_uuid ,sender_login=sender_login)
        db.add(new_request)
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")