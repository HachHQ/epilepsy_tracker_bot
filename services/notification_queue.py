import asyncio
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis
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
                keyboard = InlineKeyboardBuilder()
                base64_payload = pack_callback_data(request_uuid, transmitted_profile_id, sender_id)
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

'''
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Time, ForeignKey, select
from datetime import datetime, timedelta, time as dt_time
import pytz

# === Настройки ===
API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"

# === SQLAlchemy setup ===
Base = declarative_base()

class User(Base):
    tablename = "users"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)
    timezone = Column(String)  # Например, "Europe/Moscow"

class Notification(Base):
    tablename = "user_notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    notify_time = Column(dt_time)  # локальное время
    mode = Column(String)  # например, 'daily', 'weekdays'

engine = create_async_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# === Aiogram ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# === APScheduler ===
scheduler = AsyncIOScheduler()

def get_nearest_slot(dt: datetime):
    # округление к ближайшей четверти часа
    minute = (dt.minute // 15) * 15
    return dt.replace(minute=minute, second=0, microsecond=0)

async def process_slot_notifications(slot_time_utc: datetime):
    """
    Обрабатывает один слот — выбирает пользователей, у кого локальное время соответствует этому слоту UTC.
    """
    async with SessionLocal() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()

        for user in users:
            try:
                tz = pytz.timezone(user.timezone)
            except Exception:
                continue  # пропустить неверный timezone

            # Переводим UTC-слот во время пользователя
            user_time = slot_time_utc.astimezone(tz)
            rounded_user_time = get_nearest_slot(user_time).time()

            # Найдём, есть ли у него уведомления на это время
            notif_q = select(Notification).where(
                Notification.user_id == user.id,
                Notification.notify_time == rounded_user_time
            )
            result = await session.execute(notif_q)
            notifs = result.scalars().all()

            for notif in notifs:
                await bot.send_message(user.chat_id, f"🔔 Напоминание по режиму {notif.mode}")

# Запуск задач на каждый 15-минутный слот
def schedule_quarter_slots():
    for minute in [0, 15, 30, 45]:
        trigger = CronTrigger(minute=minute)
        scheduler.add_job(
            lambda: asyncio.create_task(process_slot_notifications(datetime.utcnow())),
            trigger=trigger,
            name=f"slot_{minute}"
        )

# === Запуск ===
async def main():
    scheduler.start()
    schedule_quarter_slots()
    await dp.start_polling()

if name == "main":
    asyncio.run(main())
'''