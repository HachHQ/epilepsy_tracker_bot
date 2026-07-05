import logging

from apscheduler.triggers.cron import CronTrigger

from adapters.telegram.medication_reminders import scheduler
from database.db_init import SessionLocal
from use_cases.retention import run_retention_purge

logger = logging.getLogger(__name__)


async def _retention_purge_job() -> None:
    async with SessionLocal() as session:
        stats = await run_retention_purge(session)
        await session.commit()
    if any((stats.seizures_deleted, stats.profiles_deleted, stats.users_deleted)):
        logger.info(
            "Retention purge completed: seizures=%s profiles=%s users=%s",
            stats.seizures_deleted,
            stats.profiles_deleted,
            stats.users_deleted,
        )


def schedule_retention_purge() -> None:
    scheduler.add_job(
        _retention_purge_job,
        trigger=CronTrigger(hour=3, minute=0),
        name="retention_purge",
        replace_existing=True,
        max_instances=1,
    )
