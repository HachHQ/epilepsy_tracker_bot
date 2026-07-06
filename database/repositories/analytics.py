import logging

from sqlalchemy import desc, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Seizure, SeizureSymptom, SeizureTrigger, Symptom, Trigger

logger = logging.getLogger(__name__)


async def get_top_seizure_features(session: AsyncSession, profile_id: int) -> dict:
    symptom_query = (
        select(Symptom.symptom_name, func.count(Symptom.id))
        .join(SeizureSymptom, Symptom.id == SeizureSymptom.symptom_id)
        .join(Seizure, Seizure.id == SeizureSymptom.seizure_id)
        .where(Symptom.profile_id == profile_id)
        .group_by(Symptom.symptom_name)
        .order_by(desc(func.count(Symptom.id)))
        .limit(5)
    )
    symptoms_result = await session.execute(symptom_query)
    top_symptoms = [{"name": name, "count": count} for name, count in symptoms_result.all()]

    trigger_query = (
        select(Trigger.trigger_name, func.count(Trigger.id))
        .join(SeizureTrigger, Trigger.id == SeizureTrigger.trigger_id)
        .join(Seizure, Seizure.id == SeizureTrigger.seizure_id)
        .where(Trigger.profile_id == profile_id)
        .group_by(Trigger.trigger_name)
        .order_by(desc(func.count(Trigger.id)))
        .limit(5)
    )
    triggers_result = await session.execute(trigger_query)
    top_triggers = [{"name": name, "count": count} for name, count in triggers_result.all()]

    type_query = (
        select(Seizure.type_of_seizure, func.count(Seizure.id))
        .where(Seizure.profile_id == profile_id)
        .where(Seizure.type_of_seizure.isnot(None))
        .group_by(Seizure.type_of_seizure)
        .order_by(desc(func.count(Seizure.id)))
        .limit(5)
    )
    types_result = await session.execute(type_query)
    top_types = [{"name": name, "count": count} for name, count in types_result.all()]

    return {
        "top_symptoms": top_symptoms,
        "top_triggers": top_triggers,
        "top_types": top_types,
    }


async def get_avg_duration_by_month(session: AsyncSession, profile_id: int, year: int):
    query = (
        select(
            extract("month", func.to_date(Seizure.date, "YYYY-MM-DD")).label("month"),
            func.avg(Seizure.duration).label("avg_duration"),
        )
        .where(
            Seizure.profile_id == profile_id,
            func.extract("year", func.to_date(Seizure.date, "YYYY-MM-DD")) == year,
            Seizure.duration.is_not(None),
        )
        .group_by("month")
        .order_by("month")
    )
    result = await session.execute(query)
    return result.all()
