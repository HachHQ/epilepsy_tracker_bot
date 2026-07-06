from collections.abc import Iterable
from datetime import date, datetime

from sqlalchemy import asc, cast, Date, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Seizure, SeizureSymptom, SeizureTrigger, Symptom, Trigger


def normalize_feature_names(value: Iterable[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [name.strip() for name in value.split(",") if name.strip()]
    return [str(name).strip() for name in value if str(name).strip()]


async def get_or_create_symptom(
    session: AsyncSession,
    name: str,
    profile_id: int,
) -> Symptom:
    symptom = await session.scalar(
        select(Symptom).where(
            Symptom.symptom_name == name,
            (Symptom.profile_id.is_(None)) | (Symptom.profile_id == profile_id),
        )
    )
    if symptom:
        return symptom

    symptom = Symptom(symptom_name=name, profile_id=profile_id)
    session.add(symptom)
    await session.flush()
    return symptom


async def get_or_create_trigger(
    session: AsyncSession,
    name: str,
    profile_id: int,
) -> Trigger:
    normalized_name = name.lower().capitalize()
    trigger = await session.scalar(
        select(Trigger).where(
            Trigger.trigger_name == normalized_name,
            (Trigger.profile_id.is_(None)) | (Trigger.profile_id == profile_id),
        )
    )
    if trigger:
        return trigger

    trigger = Trigger(trigger_name=normalized_name, profile_id=profile_id)
    session.add(trigger)
    await session.flush()
    return trigger


async def create_seizure(
    session: AsyncSession,
    *,
    profile_id: int,
    date: str,
    time: str | None,
    severity: str | None,
    duration: int | str | None,
    comment: str | None,
    count: int | str | None,
    video_tg_id: str | None,
    trigger_names: Iterable[str] | str | None,
    symptom_names: Iterable[str] | str | None,
    location: str | None,
    creator_login: str,
    type_of_seizure: str | None,
) -> Seizure:
    triggers = normalize_feature_names(trigger_names)
    symptoms = normalize_feature_names(symptom_names)

    seizure = Seizure(
        profile_id=profile_id,
        date=date,
        time=time or None,
        severity=severity or None,
        duration=int(duration) if duration else None,
        comment=comment or None,
        count=int(count) if count else None,
        video_tg_id=video_tg_id or None,
        triggers=", ".join(triggers) if triggers else None,
        symptoms=", ".join(symptoms) if symptoms else None,
        location=location or None,
        creator_login=creator_login,
        type_of_seizure=type_of_seizure or None,
    )
    session.add(seizure)
    await session.flush()

    for name in symptoms:
        symptom = await get_or_create_symptom(session, name, profile_id)
        session.add(SeizureSymptom(seizure_id=seizure.id, symptom_id=symptom.id))

    for name in triggers:
        trigger = await get_or_create_trigger(session, name, profile_id)
        session.add(SeizureTrigger(seizure_id=seizure.id, trigger_id=trigger.id))

    return seizure


async def list_profile_seizures(
    session: AsyncSession,
    profile_id: int,
    *,
    descending: bool = True,
) -> list[Seizure]:
    order = desc(Seizure.date) if descending else asc(Seizure.date)
    result = await session.execute(
        select(Seizure).where(Seizure.profile_id == int(profile_id)).order_by(order)
    )
    return list(result.scalars().all())


async def list_seizures_from_date(
    session: AsyncSession,
    profile_id: int,
    *,
    year: int,
    month: int = 1,
    day: int = 1,
) -> list[Seizure]:
    from_date = datetime(year=year, month=month, day=day)
    result = await session.execute(
        select(Seizure).where(
            cast(Seizure.date, Date) >= from_date,
            Seizure.profile_id == int(profile_id),
        )
    )
    return list(result.scalars().all())


async def list_seizures_for_year(
    session: AsyncSession,
    profile_id: int,
    year: int,
) -> list[Seizure]:
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)
    result = await session.execute(
        select(Seizure).where(
            Seizure.profile_id == int(profile_id),
            cast(Seizure.date, Date) >= start_date,
            cast(Seizure.date, Date) < end_date,
        )
    )
    return list(result.scalars().all())


async def get_average_duration(session: AsyncSession, profile_id: int):
    return await session.scalar(
        select(func.avg(Seizure.duration)).where(
            Seizure.profile_id == int(profile_id),
            Seizure.duration.is_not(None),
        )
    )


async def list_seizures_with_duration(session: AsyncSession, profile_id: int) -> list[Seizure]:
    result = await session.execute(
        select(Seizure).where(
            Seizure.profile_id == int(profile_id),
            Seizure.duration.is_not(None),
        )
    )
    return list(result.scalars().all())


async def get_seizure_by_id(
    session: AsyncSession,
    seizure_id: int,
    profile_id: int,
) -> Seizure | None:
    return await session.scalar(
        select(Seizure).where(
            Seizure.id == int(seizure_id),
            Seizure.profile_id == int(profile_id),
        )
    )


async def delete_seizure(
    session: AsyncSession,
    seizure_id: int,
    profile_id: int,
) -> bool:
    result = await session.execute(
        delete(Seizure).where(
            Seizure.id == int(seizure_id),
            Seizure.profile_id == int(profile_id),
        )
    )
    return result.rowcount > 0


async def delete_all_seizures_for_profile(session: AsyncSession, profile_id: int) -> int:
    result = await session.execute(
        delete(Seizure).where(Seizure.profile_id == int(profile_id))
    )
    return int(result.rowcount or 0)


async def delete_expired_seizures(session: AsyncSession, *, before: datetime) -> int:
    result = await session.execute(
        delete(Seizure).where(
            Seizure.retention_until.is_not(None),
            Seizure.retention_until < before,
        )
    )
    return int(result.rowcount or 0)


async def update_seizure_attribute(
    session: AsyncSession,
    seizure_id: int,
    profile_id: int,
    attribute: str,
    new_value,
) -> Seizure | None:
    seizure = await get_seizure_by_id(session, seizure_id, profile_id)
    if not seizure:
        return None
    if not hasattr(seizure, attribute):
        raise ValueError(f"Атрибут '{attribute}' не существует в модели Seizure.")
    setattr(seizure, attribute, new_value)
    return seizure
