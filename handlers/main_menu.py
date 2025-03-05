import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from database.models import User, TrustedPersonRequest, RequestStatus
from database.redis_client import redis
from services.notification_queue import NotificationQueue
from services.update_login_cache import get_cached_login
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
    lg = await get_cached_login(callback.message.chat.id)
    await callback.message.answer(
        f"Логин: {lg}\n"
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

        uuid_for_request = uuid.uuid4()

        new_request = TrustedPersonRequest(
            id = str(uuid_for_request),
            sender_id = user.id,
            recepient_id = recipient.id,
            status = RequestStatus.PENDING,
        )

        print(f"Новый запрос добавлен: {new_request}")
        await notification_queue.send_trusted_contact_request(recipient.telegram_id,  request_uuid=uuid_for_request ,sender_login=sender_login)
        db.add(new_request)
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")

@main_menu_router.callback_query(F.data.startswith("p_conf") | F.data.startswith("n_conf"))
async def process_accept_trusted_person(callback: CallbackQuery, db: AsyncSession):
    action, uuid_request = callback.data.split("|", 1)

    sender_login = callback.message.text.split('-', 1)[1].strip()
    print(sender_login)
    search_sender_result = await db.execute(select(User).filter(User.login == sender_login))
    sender = search_sender_result.scalars().first()

    search_recepient_id_result = await db.execute(select(User).filter(User.telegram_id == callback.message.chat.id))
    recepient = search_recepient_id_result.scalars().first()

    search_request_result = await db.execute(select(TrustedPersonRequest).filter((TrustedPersonRequest.id == uuid_request) & (TrustedPersonRequest.sender_id == sender.id) & (TrustedPersonRequest.recepient_id == recepient.id)))
    request = search_request_result.scalars().first()

    print(request.created_at - request.expires_at)

    if not recepient:
        await callback.message.answer("Запрос не найден. Попросите пользователя отправить новый.")
        await callback.answer()
        return

    if request.status != RequestStatus.PENDING:
        await callback.message.answer("Запрос уже был обработан ранее.")
        await callback.answer()
        return

    if action == "p_conf":
        print(datetime.utcnow(), request.expires_at)
        if datetime.utcnow() > request.expires_at:
            request.status = RequestStatus.EXPIRED
            await db.commit()
            await callback.message.answer("Время запроса истекло")
            await callback.answer()
            return
        request.status = RequestStatus.ACCEPTED
        await db.commit()
        await callback.message.answer("Запрос подтвержден")
        await callback.answer()


    if action == "n_conf":
        request.status = RequestStatus.REJECTED
        await db.commit()
        await callback.message.answer("Запрос отклонен")
        await callback.answer()
    await callback.answer()
