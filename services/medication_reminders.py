# notification_scheduler.py
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set
from dataclasses import dataclass
from enum import Enum

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

# Предполагаемые модели (адаптируйте под свою структуру)
from database.models import User, NotificationSettings
from your_database import get_session
from your_redis import redis_client

logger = logging.getLogger(__name__)


class NotificationPattern(Enum):
    DAILY = "daily"
    EVERY_2_DAYS = "every_2_days"
    EVERY_3_DAYS = "every_3_days"


@dataclass
class TimeSlot:
    hour: int
    minute: int
    def __str__(self):
        return f"{self.hour:02d}:{self.minute:02d}"
    def __hash__(self):
        return hash((self.hour, self.minute))


class NotificationScheduler:
    def __init__(self, bot: Bot, scheduler: AsyncIOScheduler):
        self.bot = bot
        self.scheduler = scheduler
        self.rate_limiter = RateLimiter(max_requests=25, time_window=1.0)
    async def initialize(self):
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                slot = TimeSlot(hour, minute)
                job_id = f"notifications_{slot}"
                self.scheduler.add_job(
                    func=self._process_time_slot,
                    trigger=CronTrigger(hour=hour, minute=minute),
                    args=[slot],
                    id=job_id,
                    replace_existing=True,
                    max_instances=1
                )
        logger.info("Инициализировано 96 временных слотов для уведомлений")
    async def _process_time_slot(self, slot: TimeSlot):
        try:
            users_to_notify = await self._get_users_for_slot(slot)
            if not users_to_notify:
                return
            logger.info(f"Обработка слота {slot}: найдено {len(users_to_notify)} пользователей")
            grouped_users = self._group_users_by_pattern(users_to_notify)
            for pattern, users in grouped_users.items():
                valid_users = await self._filter_users_by_pattern(users, pattern)
                if valid_users:
                    await self._send_notifications_batch(valid_users)
        except Exception as e:
            logger.error(f"Ошибка при обработке слота {slot}: {e}")
    async def _get_users_for_slot(self, slot: TimeSlot) -> List[User]:
        async with get_session() as session:
            users = []
            for tz_offset in range(-12, 15):
                local_datetime = datetime.now().replace(
                    hour=slot.hour,
                    minute=slot.minute,
                    second=0,
                    microsecond=0
                )
                utc_datetime = local_datetime - timedelta(hours=tz_offset)
                current_utc = datetime.utcnow()
                time_diff = abs((utc_datetime - current_utc).total_seconds())

                if time_diff <= 60:
                    timezone_str = f"UTC{'+' if tz_offset >= 0 else ''}{tz_offset}"

                    query_users = session.query(User).join(NotificationSettings).filter(
                        and_(
                            User.timezone == timezone_str,
                            NotificationSettings.is_enabled == True,
                            NotificationSettings.notification_time_hour == slot.hour,
                            NotificationSettings.notification_time_minute == slot.minute
                        )
                    ).all()
                    users.extend(query_users)
            return users

    def _group_users_by_pattern(self, users: List[User]) -> Dict[NotificationPattern, List[User]]:
        grouped = {pattern: [] for pattern in NotificationPattern}
        for user in users:
            pattern = NotificationPattern(user.notification_settings.pattern)
            grouped[pattern].append(user)
        return {k: v for k, v in grouped.items() if v}

    async def _filter_users_by_pattern(self, users: List[User], pattern: NotificationPattern) -> List[User]:
        if pattern == NotificationPattern.DAILY:
            return users
        valid_users = []
        current_date = datetime.now().date()
        for user in users:
            cache_key = f"last_notification:{user.id}"
            last_notification_str = await redis_client.get(cache_key)
            if not last_notification_str:
                valid_users.append(user)
                continue
            try:
                last_notification_date = datetime.fromisoformat(last_notification_str).date()
                days_diff = (current_date - last_notification_date).days
                if pattern == NotificationPattern.EVERY_2_DAYS and days_diff >= 2:
                    valid_users.append(user)
                elif pattern == NotificationPattern.EVERY_3_DAYS and days_diff >= 3:
                    valid_users.append(user)
            except (ValueError, TypeError):
                valid_users.append(user)

        return valid_users

    async def _send_notifications_batch(self, users: List[User]):
        for user in users:
            try:
                await self.rate_limiter.acquire()
                message_text = await self._get_notification_message(user)
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message_text
                )
                cache_key = f"last_notification:{user.id}"
                await redis_client.set(
                    cache_key,
                    datetime.now().isoformat(),
                    ex=86400 * 7
                )
                logger.debug(f"Уведомление отправлено пользователю {user.telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {user.telegram_id}: {e}")

    async def _get_notification_message(self, user: User) -> str:
        return f"🔔 Напоминание для {user.name}!\n\nВремя выполнить запланированные задачи."

    @staticmethod
    def round_to_quarter_hour(hour: int, minute: int) -> TimeSlot:
        if minute < 8:
            return TimeSlot(hour, 0)
        elif minute < 23:
            return TimeSlot(hour, 15)
        elif minute < 38:
            return TimeSlot(hour, 30)
        elif minute < 53:
            return TimeSlot(hour, 45)
        else:
            next_hour = (hour + 1) % 24
            return TimeSlot(next_hour, 0)

class RateLimiter:
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = asyncio.Lock()
    async def acquire(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            self.requests = [req_time for req_time in self.requests
                           if now - req_time < self.time_window]
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            self.requests.append(now)

async def set_user_notification(
    user_id: int,
    hour: int,
    minute: int,
    pattern: NotificationPattern,
    timezone: str
):
    slot = NotificationScheduler.round_to_quarter_hour(hour, minute)
    async with get_session() as session:
        settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
        if not settings:
            settings = NotificationSettings(user_id=user_id)
            session.add(settings)
        settings.is_enabled = True
        settings.notification_time_hour = slot.hour
        settings.notification_time_minute = slot.minute
        settings.pattern = pattern.value
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.timezone = timezone
        session.commit()
    return slot

async def disable_user_notifications(user_id: int):
    async with get_session() as session:
        settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
        if settings:
            settings.is_enabled = False
            session.commit()

async def setup_notification_scheduler(bot: Bot, scheduler: AsyncIOScheduler):

    notification_scheduler = NotificationScheduler(bot, scheduler)
    await notification_scheduler.initialize()
    return notification_scheduler


# Пример использования в хендлерах
"""
"""
# В файле с хендлерами
from notification_scheduler import set_user_notification, NotificationPattern

@router.message(Command("set_reminder"))
async def set_reminder_handler(message: Message):
    # Парсинг команды пользователя
    # /set_reminder 09:30 every_2_days

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Неверный формат. Используйте: /set_reminder ЧЧ:ММ паттерн")
        return

    try:
        time_str = parts[1]
        pattern_str = parts[2]

        hour, minute = map(int, time_str.split(':'))
        pattern = NotificationPattern(pattern_str)

        # Получаем часовой пояс пользователя (например, из базы или спрашиваем)
        user_timezone = "UTC+3"  # Пример

        slot = await set_user_notification(
            user_id=message.from_user.id,
            hour=hour,
            minute=minute,
            pattern=pattern,
            timezone=user_timezone
        )

        await message.answer(
            f"✅ Уведомление установлено на {slot} по вашему времени\n"
            f"Паттерн: {pattern.value}"
        )

    except Exception as e:
        await message.answer(f"Ошибка при установке уведомления: {e}")
"""

'''
import asyncio
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

def get_nearest_slot(dt: datetime) -> datetime:
    separators = [7, 22, 37, 52]
    minute = dt.minute
    hour = dt.hour
    if minute <= separators[0]:
        slot_minute = 0
    elif minute <= separators[1]:
        slot_minute = 15
    elif minute <= separators[2]:
        slot_minute = 30
    elif minute <= separators[3]:
        slot_minute = 45
    else:
        dt += timedelta(hours=1)
        dt = dt.replace(minute=0, second=0, microsecond=0)
        return dt
    return dt.replace(minute=slot_minute, second=0, microsecond=0)

async def process_slot_notifications(slot_time_utc: datetime):
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

import asyncio
from datetime import datetime, timedelta, time as dt_time
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import Column, Integer, String, ForeignKey, Time, select
from sqlalchemy.orm import sessionmaker
from database.db_init import SessionLocal
from functools import partial
from database.models import User, UserNotifications
from keyboards.notification_kb import get_confirm_of_notification_message

from asyncio import Queue

notification_queue = Queue()

async def throttled_worker(bot: Bot):
    while True:
        chat_id, text = await notification_queue.get()
        try:

            if not text:
                raise ValueError("Пустой текст сообщения")
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=get_confirm_of_notification_message())
        except Exception as e:
            print(f"[Ошибка] chat_id={chat_id}: {e}")
        await asyncio.sleep(0.05)
        notification_queue.task_done()

async def start_workers(bot: Bot, n=5):
    for _ in range(n):
        asyncio.create_task(throttled_worker(bot))

def get_nearest_slot(dt: datetime) -> datetime:
    separators = [7, 22, 37, 52]
    minute = dt.minute
    if minute <= separators[0]:
        slot_minute = 0
    elif minute <= separators[1]:
        slot_minute = 15
    elif minute <= separators[2]:
        slot_minute = 30
    elif minute <= separators[3]:
        slot_minute = 45
    else:
        dt += timedelta(hours=1)
        dt = dt.replace(minute=0, second=0, microsecond=0)
        return dt
    return dt.replace(minute=slot_minute, second=0, microsecond=0)

def convert_utc_to_user_time(utc_dt: datetime, tz_offset_str: str) -> datetime:
    try:
        offset = int(tz_offset_str)
        return utc_dt + timedelta(hours=offset)
    except ValueError:
        return utc_dt

async def process_slot_notifications(slot_time_utc: datetime):
    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            user_time = convert_utc_to_user_time(slot_time_utc, user.timezone)
            slot_time = get_nearest_slot(user_time).time()
            notif_query = select(UserNotifications).where(
                UserNotifications.user_id == user.id,
                UserNotifications.notify_time == slot_time,
                UserNotifications.is_enabled == True
            )
            result = await session.execute(notif_query)
            notifications = result.scalars().all()
            for notif in notifications:
                await notification_queue.put((user.telegram_id, f"🔔 Напоминание: {notif.note}"))


scheduler = AsyncIOScheduler()

from functools import partial

def schedule_notification_slots():
    for minute in [0, 15, 30, 45]:
        async def slot_job(slot_minute):
            print(f"Выполняем слот: {slot_minute}")
            await process_slot_notifications(datetime.utcnow())

        trigger = CronTrigger(minute=minute)
        scheduler.add_job(partial(slot_job, minute), trigger=trigger, name=f"slot_{minute}")
