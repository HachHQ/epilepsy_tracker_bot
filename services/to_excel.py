import logging
import uuid
from datetime import datetime, time as time_class
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Seizure, SeizureSymptom, SeizureTrigger, Symptom, Trigger
from i18n import get_excel_export_headers, t

Path("temp_tables").mkdir(exist_ok=True)
logger = logging.getLogger(__name__)

EXCEL_TEMPLATE_PATH = "template_seizures.xlsx"

EXPECTED_COLUMNS = [
    "date", "time", "severity", "duration", "comment",
    "type_of_seizure", "location", "triggers", "symptoms",
]


async def build_seizures_excel(profile_id: int, db: AsyncSession) -> str:
    headers = get_excel_export_headers()
    result = await db.execute(select(Seizure).where(Seizure.profile_id == int(profile_id)))
    seizures = result.scalars().all()
    data = []
    for seizure in seizures:
        seizure_id = seizure.id
        result = await db.execute(
            select(Symptom.symptom_name)
            .join(SeizureSymptom, Symptom.id == SeizureSymptom.symptom_id)
            .where(SeizureSymptom.seizure_id == seizure_id)
        )
        symptoms = [row[0] for row in result.fetchall()]
        result = await db.execute(
            select(Trigger.trigger_name)
            .join(SeizureTrigger, Trigger.id == SeizureTrigger.trigger_id)
            .where(SeizureTrigger.seizure_id == seizure_id)
        )
        triggers = [row[0] for row in result.fetchall()]
        row = {
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
        data.append({headers[key]: row[key] for key in headers})
    df = pd.DataFrame(data)
    path = f"temp_tables/{uuid.uuid4().hex}_seizure_report.xlsx"
    df.to_excel(path, index=False)
    return path


def get_excel_template_path() -> str:
    return EXCEL_TEMPLATE_PATH


def validate_row(row: pd.Series) -> bool:
    try:
        if pd.isna(row["date"]):
            return False
        pd.to_datetime(row["date"], dayfirst=True, errors="raise")
        time_value = row.get("time")
        if pd.notna(time_value):
            if isinstance(time_value, time_class):
                pass
            elif isinstance(time_value, datetime):
                time_value = time_value.time()
            elif isinstance(time_value, float):
                total_seconds = int(time_value * 86400)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                time_value = time_class(hour=hours, minute=minutes)
            elif isinstance(time_value, str):
                time_value = datetime.strptime(time_value.strip(), "%H:%M").time()
            else:
                return False
        duration_value = row.get("duration")
        if pd.notna(duration_value) and not isinstance(duration_value, (int, float)):
            return False
        return True
    except Exception:
        logger.exception("Invalid Excel row")
        return False


async def get_or_create_symptom(db: AsyncSession, name: str, profile_id: int):
    result = await db.execute(select(Symptom).where(Symptom.symptom_name == name, Symptom.profile_id == profile_id))
    symptom = result.scalars().first()
    if symptom:
        return symptom
    symptom = Symptom(symptom_name=name, profile_id=profile_id)
    db.add(symptom)
    await db.flush()
    return symptom


async def get_or_create_trigger(db: AsyncSession, name: str, profile_id: int):
    result = await db.execute(select(Trigger).where(Trigger.trigger_name == name, Trigger.profile_id == profile_id))
    trigger = result.scalars().first()
    if trigger:
        return trigger
    trigger = Trigger(trigger_name=name, profile_id=profile_id)
    db.add(trigger)
    await db.flush()
    return trigger


def parse_excel_time(time_value) -> time_class | None:
    if pd.isna(time_value):
        return None
    if isinstance(time_value, time_class):
        return time_value
    if isinstance(time_value, datetime):
        return time_value.time()
    if isinstance(time_value, float):
        total_seconds = int(time_value * 86400)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return time_class(hour=hours, minute=minutes)
    if isinstance(time_value, str):
        try:
            return datetime.strptime(time_value.strip(), "%H:%M").time()
        except ValueError:
            pass
    return None


async def import_seizures_from_xlsx(
    file_path: str,
    db: AsyncSession,
    profile_id: int,
    login: str,
) -> tuple[int, list]:
    df = pd.read_excel(file_path)
    if set(EXPECTED_COLUMNS) - set(df.columns):
        raise ValueError(t("excel.missing_columns"))
    failed_rows = []
    success_count = 0
    for index, row in df.iterrows():
        if not validate_row(row):
            failed_rows.append(row.to_dict())
            continue
        try:
            raw_date = pd.to_datetime(row["date"], dayfirst=True)
            raw_time = parse_excel_time(row["time"])
            seizure = Seizure(
                profile_id=int(profile_id),
                date=raw_date.strftime("%Y-%m-%d"),
                time=raw_time.strftime("%H:%M") if raw_time else None,
                severity=str(row.get("severity")) if pd.notna(row.get("severity")) else None,
                duration=int(row["duration"]) if pd.notna(row["duration"]) else None,
                comment=row.get("comment") if pd.notna(row.get("comment")) else None,
                type_of_seizure=row.get("type_of_seizure") if pd.notna(row.get("type_of_seizure")) else None,
                location=row.get("location") if pd.notna(row.get("location")) else None,
                creator_login=login,
            )
            db.add(seizure)
            await db.flush()
            if pd.notna(row.get("symptoms")):
                symptom_names = [s.strip() for s in str(row["symptoms"]).split(",")]
                for name in symptom_names:
                    symptom = await get_or_create_symptom(db, name, profile_id)
                    db.add(SeizureSymptom(seizure_id=seizure.id, symptom_id=symptom.id))
            if pd.notna(row.get("triggers")):
                trigger_names = [name.strip() for name in str(row["triggers"]).split(",")]
                for name in trigger_names:
                    trigger = await get_or_create_trigger(db, name, profile_id)
                    db.add(SeizureTrigger(seizure_id=seizure.id, trigger_id=trigger.id))
            success_count += 1
        except Exception:
            logger.exception("Failed to import Excel row %s", index)
            await db.rollback()
            failed_rows.append(row.to_dict())
    return success_count, failed_rows
