import asyncio
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

class NotificationQueue:
    def __init__(self, bot: Bot, rate_limit: float = 0.05):
        self.bot = bot
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
                chat_id, text, kwargs = await self.queue.get()
                reciver_kb_bd = InlineKeyboardBuilder()
                reciver_kb_bd.button(text="Да", callback_data="p_conf")
                reciver_kb_bd.button(text="Нет", callback_data="n_conf")
                try:
                    await self.bot.send_message(chat_id, text, reply_markup=reciver_kb_bd.as_markup(), **kwargs)
                except Exception as e:
                    print(f"Ошибка отправки уведомления для chat_id {chat_id}: {e}")
                await asyncio.sleep(self.rate_limit)
            except asyncio.CancelledError:
                break

    async def send_notification(self, chat_id: int, text: str, **kwargs):
        await self.queue.put((chat_id, text, kwargs))

notification_queue = None

def set_notification_queue(nq: NotificationQueue):
    global notification_queue
    notification_queue = nq

def get_notification_queue() -> NotificationQueue:
    return notification_queue
