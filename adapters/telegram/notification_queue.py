import asyncio
import logging
from abc import ABC, abstractmethod

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.notification_kb import get_confirm_of_notification_message
from services.hmac_encrypt import pack_callback_data

logger = logging.getLogger(__name__)


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
                logger.info("Notification sent to user %s", uid)
                await asyncio.sleep(0.05)
            except Exception:
                logger.exception("Failed to send notification to user %s", uid)


class TrustedContactRequest(NotificationBase):
    def __init__(
        self,
        chat_id: int,
        request_uuid: str,
        sender_login: str,
        sender_id: int,
        transmitted_profile_id: int,
    ):
        self.chat_id = chat_id
        self.request_uuid = request_uuid
        self.sender_login = sender_login
        self.sender_id = sender_id
        self.transmitted_profile_id = transmitted_profile_id

    async def send(self, bot: Bot):
        keyboard = InlineKeyboardBuilder()
        base64_payload = pack_callback_data(
            self.request_uuid, self.transmitted_profile_id, self.sender_id
        )
        keyboard.button(text="Да", callback_data=f"p_conf|{base64_payload}")
        keyboard.button(text="Нет", callback_data=f"n_conf|{base64_payload}")
        try:
            await bot.send_message(
                self.chat_id,
                f"Подтвердите запрос доверенного лица - {self.sender_login}",
                reply_markup=keyboard.as_markup(),
            )
            logger.info("Trusted contact request sent to chat %s", self.chat_id)
        except Exception:
            logger.exception("Failed to send trusted contact request")


class MedicationReminderNotification(NotificationBase):
    def __init__(self, chat_id: int, text: str):
        self.chat_id = chat_id
        self.text = text

    async def send(self, bot: Bot):
        try:
            if not self.text:
                raise ValueError("Empty notification text")
            await bot.send_message(
                chat_id=self.chat_id,
                text=self.text,
                reply_markup=get_confirm_of_notification_message(),
            )
            logger.info("Medication reminder sent to chat %s", self.chat_id)
        except Exception:
            logger.exception("Failed to send reminder to chat_id=%s", self.chat_id)


class NotificationQueue:
    def __init__(self, bot: Bot, redis=None, rate_limit: float = 0.05):
        self.bot = bot
        self.redis = redis
        self.queue: asyncio.Queue[NotificationBase] = asyncio.Queue()
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
                notification = await self.queue.get()
                try:
                    await notification.send(self.bot)
                finally:
                    self.queue.task_done()
                await asyncio.sleep(self.rate_limit)
            except asyncio.CancelledError:
                break

    async def enqueue(self, notification: NotificationBase):
        await self.queue.put(notification)
