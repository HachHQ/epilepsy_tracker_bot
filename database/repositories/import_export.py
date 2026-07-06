from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SeizureSymptom, SeizureTrigger, Symptom, Trigger
from database.repositories.seizures import list_profile_seizures


async def list_seizure_export_rows(session: AsyncSession, profile_id: int) -> list[dict]:
    seizures = await list_profile_seizures(session, profile_id, descending=False)
    rows: list[dict] = []
    for seizure in seizures:
        symptoms_result = await session.execute(
            select(Symptom.symptom_name)
            .join(SeizureSymptom, Symptom.id == SeizureSymptom.symptom_id)
            .where(SeizureSymptom.seizure_id == seizure.id)
        )
        symptoms = [row[0] for row in symptoms_result.fetchall()]
        triggers_result = await session.execute(
            select(Trigger.trigger_name)
            .join(SeizureTrigger, Trigger.id == SeizureTrigger.trigger_id)
            .where(SeizureTrigger.seizure_id == seizure.id)
        )
        triggers = [row[0] for row in triggers_result.fetchall()]
        rows.append(
            {
                "date": seizure.date,
                "time": seizure.time,
                "severity": seizure.severity,
                "duration": seizure.duration,
                "comment": seizure.comment,
                "type_of_seizure": seizure.type_of_seizure,
                "location": seizure.location,
                "triggers": ", ".join(triggers),
                "symptoms": ", ".join(symptoms),
            }
        )
    return rows
