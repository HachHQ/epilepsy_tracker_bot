import asyncio
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis
from database.db_init import SessionLocal
from services.hmac_encrypt import pack_callback_data

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
                chat_id, sender_id, request_uuid, text, transmitted_profile_id, kwargs = await self.queue.get()
                print("чат айди", chat_id)
                print("uuid", request_uuid)
                print("текст", text)
                print("Кварги", kwargs)
                keyboard = InlineKeyboardBuilder()
                base64_payload = pack_callback_data(request_uuid, transmitted_profile_id, sender_id)
                print(base64_payload)
                keyboard.button(text="Да", callback_data=f"p_conf|{base64_payload}")
                keyboard.button(text="Нет", callback_data=f"n_conf|{base64_payload}")
                try:
                    await self.bot.send_message(chat_id, text, reply_markup=keyboard.as_markup(), **kwargs)
                    print("Уведомление успешно отправлено")
                except Exception as e:
                    print(f"Ошибка отправки уведомления {chat_id}: {e}")
                await asyncio.sleep(self.rate_limit)
            except asyncio.CancelledError:
                break

    async def send_notification(self, chat_id: int, text: str, **kwargs):
        await self.queue.put((chat_id, text, kwargs))

    #TODO write a funcion for regular notification about medication time


    #TODO prohibit entering your own login

    async def send_trusted_contact_request(self,
                                           chat_id: int,
                                           request_uuid: str,
                                           sender_login: str,
                                           sender_id: int,
                                           transmitted_profile_id: int,
                                           **kwargs):
        text = f"Подтвердите запрос доверенного лица - {sender_login}"
        await self.queue.put((chat_id, sender_id, request_uuid, text, transmitted_profile_id, {}))


    """async def check_and_send_reminders(self):
        Фоновая задача для рассылки напоминаний о приеме лекарств
        while self.running:
            async with SessionLocal() as session:
                contacts = session.query(TrustedContact).filter(TrustedContact.needs_reminder == True).all()

                for contact in contacts:
                    await self.send_notification(contact.user_id, "Не забудьте принять лекарство!")
                    contact.last_reminder_sent = datetime.utcnow()
                    session.commit()

            await asyncio.sleep(3600)  # Запускать каждый час"""
