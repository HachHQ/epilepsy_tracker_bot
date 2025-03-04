import asyncio
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis
from database.db_init import SessionLocal
# from database.models import TrustedContact

class NotificationQueue:
    def __init__(self, bot: Bot, redis: Redis, rate_limit: float = 0.05):
        self.bot = bot
        self.redis = redis
        self.queue = asyncio.Queue()
        self.rate_limit = rate_limit
        self.worker_task = None
        self.running = False

    async def start(self):
        """Запуск фонового воркера"""
        self.running = True
        self.worker_task = asyncio.create_task(self.worker())

    async def stop(self):
        """Остановка воркера"""
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    async def worker(self):
        """Обрабатывает очередь уведомлений"""
        while self.running:
            try:
                chat_id, request_uuid, text, kwargs = await self.queue.get()
                print("чат айди", chat_id)
                print("uuid", request_uuid)
                print("текст", text)
                print("Кварги", kwargs)
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="Да", callback_data=f"p_conf|{request_uuid}")
                keyboard.button(text="Нет", callback_data="n_conf")

                try:
                    await self.bot.send_message(chat_id, text, reply_markup=keyboard.as_markup(), **kwargs)
                    print("Уведомление успешно отправлено")
                except Exception as e:
                    print(f"Ошибка отправки уведомления {chat_id}: {e}")
                await asyncio.sleep(self.rate_limit)
            except asyncio.CancelledError:
                break

    async def send_notification(self, chat_id: int, text: str, **kwargs):
        """Добавляет сообщение в очередь"""
        await self.queue.put((chat_id, text, kwargs))

    async def send_trusted_contact_request(self, chat_id: int, request_uuid: str, sender_login: str, **kwargs):
        """Отправляет запрос на подтверждение доверенного лица"""

        text = f"Подтвердите запрос доверенного лица -{sender_login}"
        await self.queue.put((chat_id, request_uuid, text, {}))

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






# import asyncio
# from aiogram import Bot
# from aiogram.utils.keyboard import InlineKeyboardBuilder

# class NotificationQueue:
#     def __init__(self, bot: Bot, rate_limit: float = 0.05):
#         self.bot = bot
#         self.queue = asyncio.Queue()
#         self.rate_limit = rate_limit
#         self.worker_task = None
#         self.running = False

#     async def start(self):
#         self.running = True
#         self.worker_task = asyncio.create_task(self.worker())

#     async def stop(self):
#         self.running = False
#         if self.worker_task:
#             self.worker_task.cancel()
#             try:
#                 await self.worker_task
#             except asyncio.CancelledError:
#                 pass

#     async def worker(self):
#         while self.running:
#             try:
#                 chat_id, text, kwargs = await self.queue.get()
#                 reciver_kb_bd = InlineKeyboardBuilder()
#                 reciver_kb_bd.button(text="Да", callback_data="p_conf")
#                 reciver_kb_bd.button(text="Нет", callback_data="n_conf")
#                 try:
#                     await self.bot.send_message(chat_id, text, reply_markup=reciver_kb_bd.as_markup(), **kwargs)
#                 except Exception as e:
#                     print(f"Ошибка отправки уведомления для chat_id {chat_id}: {e}")
#                 await asyncio.sleep(self.rate_limit)
#             except asyncio.CancelledError:
#                 break

#     async def send_notification(self, chat_id: int, text: str, **kwargs):
#         await self.queue.put((chat_id, text, kwargs))

# notification_queue = None

# def set_notification_queue(nq: NotificationQueue):
#     global notification_queue
#     notification_queue = nq

# def get_notification_queue() -> NotificationQueue:
#     return notification_queue
