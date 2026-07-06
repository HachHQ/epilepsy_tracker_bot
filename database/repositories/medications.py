from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MedicationCourse


def _parse_optional_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    return None


async def list_profile_medications(
    session: AsyncSession,
    profile_id: int,
) -> list[MedicationCourse]:
    result = await session.execute(
        select(MedicationCourse).where(MedicationCourse.profile_id == int(profile_id))
    )
    return list(result.scalars().all())


async def get_medication_by_id(
    session: AsyncSession,
    profile_id: int,
    medication_id: int,
) -> MedicationCourse | None:
    return await session.scalar(
        select(MedicationCourse).where(
            MedicationCourse.profile_id == int(profile_id),
            MedicationCourse.id == int(medication_id),
        )
    )


async def create_medication_course(
    session: AsyncSession,
    *,
    profile_id: int,
    medication_name: str | None,
    dosage: str | None,
    frequency: str | None,
    notes: str | None,
    start_date: str | date | datetime | None,
    end_date: str | date | datetime | None,
) -> MedicationCourse:
    course = MedicationCourse(
        profile_id=int(profile_id),
        medication_name=medication_name,
        dosage=dosage,
        frequency=frequency,
        notes=notes,
        start_date=_parse_optional_date(start_date),
        end_date=_parse_optional_date(end_date),
    )
    session.add(course)
    await session.flush()
    return course


async def update_medication_attribute(
    session: AsyncSession,
    profile_id: int,
    medication_id: int,
    attribute: str,
    new_value,
) -> MedicationCourse | None:
    course = await get_medication_by_id(session, profile_id, medication_id)
    if not course:
        return None
    if not hasattr(course, attribute):
        raise ValueError(f"Атрибут '{attribute}' не существует в модели MedicationCourse.")
    setattr(course, attribute, new_value)
    await session.flush()
    return course


async def delete_medication(
    session: AsyncSession,
    profile_id: int,
    medication_id: int,
) -> bool:
    result = await session.execute(
        delete(MedicationCourse).where(
            MedicationCourse.id == int(medication_id),
            MedicationCourse.profile_id == int(profile_id),
        )
    )
    return result.rowcount > 0
