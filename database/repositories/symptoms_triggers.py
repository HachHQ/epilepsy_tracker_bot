import logging

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Seizure, SeizureSymptom, Symptom, Trigger
from database.repositories.seizures import fold_symptom_counts

logger = logging.getLogger(__name__)


async def list_global_symptoms(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Symptom.symptom_name).where(Symptom.profile_id.is_(None))
    )
    return [row.symptom_name for row in result.all()]


async def list_global_triggers(session: AsyncSession) -> list[str]:
    try:
        result = await session.execute(
            select(Trigger.trigger_name).where(Trigger.profile_id.is_(None))
        )
        return [row.trigger_name for row in result.fetchall()]
    except Exception:
        logger.exception("Failed to load global triggers")
        return []


async def list_profile_symptoms(session: AsyncSession, profile_id: int) -> list[str] | None:
    result = await session.execute(
        select(Symptom.symptom_name, func.count(SeizureSymptom.seizure_id))
        .join(SeizureSymptom, SeizureSymptom.symptom_id == Symptom.id)
        .join(Seizure, Seizure.id == SeizureSymptom.seizure_id)
        .where(
            Symptom.profile_id == int(profile_id),
            Seizure.profile_id == int(profile_id),
        )
        .group_by(Symptom.symptom_name)
        .order_by(desc(func.count(SeizureSymptom.seizure_id)), Symptom.symptom_name)
    )
    names = [
        name
        for name, _count in fold_symptom_counts(
            [(str(name), int(count)) for name, count in result.all()]
        )
    ]
    return names if names else None


async def list_profile_triggers(session: AsyncSession, profile_id: int) -> list[str]:
    try:
        result = await session.execute(
            select(Trigger.trigger_name).where(Trigger.profile_id == int(profile_id))
        )
        return [row.trigger_name.capitalize() for row in result.fetchall()]
    except Exception:
        logger.exception("Failed to load profile triggers")
        return []
