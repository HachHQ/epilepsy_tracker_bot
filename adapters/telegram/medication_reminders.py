import logging
from datetime import UTC, datetime
from functools import partial

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from i18n import t
from adapters.telegram.notification_queue import MedicationReminderNotification, NotificationQueue
from database.db_init import SessionLocal
from database.models import User, UserNotifications
from services.medication_slots import convert_utc_to_user_time, get_nearest_slot

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def process_slot_notifications(notification_queue: NotificationQueue) -> None:
    async with SessionLocal() as session:
        users_result = await session.execute(
            select(User).where(User.deleted_at.is_(None))
        )
        users = users_result.scalars().all()

        for user in users:
            user_time = convert_utc_to_user_time(datetime.now(UTC), user.timezone)
            slot_time = get_nearest_slot(user_time).time()
            notifications_result = await session.execute(
                select(UserNotifications).where(
                    UserNotifications.user_id == user.id,
                    UserNotifications.notify_time == slot_time,
                    UserNotifications.is_enabled.is_(True),
                )
            )
            for notification in notifications_result.scalars().all():
                await notification_queue.enqueue(
                    MedicationReminderNotification(
                        user.telegram_id,
                        t("notification.medication_reminder", note=notification.note),
                    )
                )


async def _slot_job(notification_queue: NotificationQueue, slot_minute: int) -> None:
    logger.info("Processing reminder slot: %s", slot_minute)
    await process_slot_notifications(notification_queue)


def schedule_notification_slots(notification_queue: NotificationQueue) -> None:
    for minute in [0, 15, 30, 45]:
        scheduler.add_job(
            partial(_slot_job, notification_queue, minute),
            trigger=CronTrigger(minute=minute),
            name=f"slot_{minute}",
            replace_existing=True,
            max_instances=1,
        )
