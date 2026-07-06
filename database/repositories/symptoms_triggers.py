import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Symptom, Trigger

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
        select(Symptom.symptom_name).where(Symptom.profile_id == profile_id)
    )
    names = [row.symptom_name for row in result.all()]
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
