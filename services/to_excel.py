# modules/export_to_excel.py
import os
import uuid
from datetime import datetime, time as time_class
from aiogram import Bot
import pandas as pd
from pathlib import Path
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram.types import FSInputFile, Message
from database.models import Seizure, SeizureSymptom, SeizureTrigger, Symptom, Trigger

Path("temp_tables").mkdir(exist_ok=True)

async def export_seizures_to_excel(profile_id: int, db: AsyncSession, bot: Bot, message: Message) -> BytesIO:
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
        data.append({
            "Дата": seizure.date,
            "Время": seizure.time,
            "Степень тяжести": seizure.severity,
            "Длительность (в секундах)": seizure.duration,
            "Комментарий": seizure.comment,
            "Тип приступа": seizure.type_of_seizure,
            "Локация": seizure.location,
            "Триггеры": ", ".join(triggers),
            "Симптомы": ", ".join(symptoms),
        })
    df = pd.DataFrame(data)
    path = f'temp_tables/{uuid.uuid4().hex}_seizure_report.xlsx'
    df.to_excel(path, index=False)
    try:
        await bot.send_document(chat_id=message.chat.id, document=FSInputFile(path))
    finally:
        if os.path.exists(path):
            os.remove(path)

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Seizure, Symptom, Trigger, SeizureSymptom, SeizureTrigger
from datetime import datetime


EXPECTED_COLUMNS = [
    "date", "time", "severity", "duration", "comment",
    "type_of_seizure", "location", "triggers", "symptoms"
]


def validate_row(row: pd.Series) -> bool:
    try:

        if pd.isna(row["date"]):
            return False
        pd.to_datetime(row["date"], dayfirst=True, errors='raise')
        time_value = row.get("time")
        if pd.notna(time_value):
            if isinstance(time_value, time_class):
                pass  # уже OK
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

    except Exception as e:
        print("Ошибка:", e)
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
    elif isinstance(time_value, datetime):
        return time_value.time()
    elif isinstance(time_value, float):
        total_seconds = int(time_value * 86400)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return time_class(hour=hours, minute=minutes)
    elif isinstance(time_value, str):
        try:
            return datetime.strptime(time_value.strip(), "%H:%M").time()
        except ValueError:
            pass
    return None

async def import_seizures_from_xlsx(file_path: str, db: AsyncSession, profile_id: int, bot: Bot, message: Message, login: str):
    df = pd.read_excel(file_path)
    if set(EXPECTED_COLUMNS) - set(df.columns):
        raise ValueError("Файл не содержит все необходимые колонки")
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
                trigger_names = [t.strip() for t in str(row["triggers"]).split(",")]
                for name in trigger_names:
                    trigger = await get_or_create_trigger(db, name, profile_id)
                    db.add(SeizureTrigger(seizure_id=seizure.id, trigger_id=trigger.id))
            success_count += 1
        except Exception as e:
            print(f"Ошибка при обработке строки {index}: {e}")
            await db.rollback()
            failed_rows.append(row.to_dict())
    return success_count, failed_rows

async def generate_excel_template(bot: Bot, message: Message):
    file_path = "template_seizures.xlsx"
    text="Вот шаблон таблицы, в которую можно внести имеющиеся у вас данные. Заполняйте поля учитывая типы данных и примеры в скобках к каждому признаку."
    await bot.send_document(chat_id=message.chat.id, document=FSInputFile(file_path), caption=text)
