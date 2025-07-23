import asyncio
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis
from services.hmac_encrypt import pack_callback_data

from abc import ABC, abstractmethod

class NotificationBase(ABC):
    @abstractmethod
    async def send(self, bot: Bot):
        pass

class SosMassNotification(NotificationBase):
    def __init__(self, user_ids: list[int], text: str):
        self.user_ids = user_ids
        self.text = text

    async def send(self, bot: Bot):
        for uid in self.user_ids:
            try:
                await bot.send_message(uid, self.text)
                print(f'Уведомление выслано пользователю - {uid}')
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"❌ Ошибка при отправке пользователю {uid}: {e}")

class TrustedContactRequest(NotificationBase):
    def __init__(self,
                 chat_id: int,
                 request_uuid: str,
                 sender_login: str,
                 sender_id: int,
                 transmitted_profile_id: int):
        self.chat_id = chat_id
        self.request_uuid = request_uuid
        self.sender_login = sender_login
        self.sender_id = sender_id
        self.transmitted_profile_id = transmitted_profile_id

    async def send(self, bot: Bot):
        keyboard = InlineKeyboardBuilder()
        base64_payload = pack_callback_data(self.request_uuid, self.transmitted_profile_id, self.sender_id)
        keyboard.button(text="Да", callback_data=f"p_conf|{base64_payload}")
        keyboard.button(text="Нет", callback_data=f"n_conf|{base64_payload}")
        try:
            await bot.send_message(
                self.chat_id,
                f"Подтвердите запрос доверенного лица - {self.sender_login}",
                reply_markup=keyboard.as_markup()
            )
            print(f"✅ Запрос доверенного лица отправлен: {self.chat_id}")
        except Exception as e:
            print(f"❌ Ошибка при отправке доверенного запроса: {e}")

class NotificationQueue:
    def __init__(self, bot: Bot, redis: Redis, rate_limit: float = 0.05):
        self.bot = bot
        self.redis = redis
        self.queue = asyncio.Queue()
        self.rate_limit = rate_limit
        self.worker_task = None
        self.running = False

    async def start(self):
        self.running = True
        self.worker_task = asyncio.create_task(self.worker())

    async def stop(self):
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    async def worker(self):
        while self.running:
            try:
                obj = await self.queue.get()
                if isinstance(obj, NotificationBase):
                    await obj.send(self.bot)
                else:
                    print("⚠️ Получен объект, не реализующий интерфейс NotificationBase")
                await asyncio.sleep(self.rate_limit)
            except asyncio.CancelledError:
                break

    async def enqueue(self, notification: NotificationBase):
        await self.queue.put(notification)
