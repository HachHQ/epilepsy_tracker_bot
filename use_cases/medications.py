from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MedicationCourse
from database.repositories.medications import (
    create_medication_course,
    delete_medication,
    get_medication_by_id,
    list_profile_medications,
    update_medication_attribute,
)


@dataclass(frozen=True)
class CreateMedicationResult:
    course: MedicationCourse


@dataclass(frozen=True)
class UpdateMedicationResult:
    updated: bool
    course: MedicationCourse | None = None


@dataclass(frozen=True)
class DeleteMedicationResult:
    deleted: bool


async def list_courses(session: AsyncSession, profile_id: int) -> list[MedicationCourse]:
    return await list_profile_medications(session, profile_id)


async def get_course(
    session: AsyncSession,
    profile_id: int,
    medication_id: int,
) -> MedicationCourse | None:
    return await get_medication_by_id(session, profile_id, medication_id)


async def create_course_from_form(
    session: AsyncSession,
    *,
    profile_id: int,
    medication_name: str | None,
    dosage: str | None,
    frequency: str | None,
    notes: str | None,
    start_date: str | date | datetime | None,
    end_date: str | date | datetime | None,
) -> CreateMedicationResult:
    course = await create_medication_course(
        session,
        profile_id=profile_id,
        medication_name=medication_name,
        dosage=dosage,
        frequency=frequency,
        notes=notes,
        start_date=start_date,
        end_date=end_date,
    )
    return CreateMedicationResult(course=course)


async def update_course_field(
    session: AsyncSession,
    *,
    profile_id: int,
    medication_id: int,
    attribute: str,
    new_value,
) -> UpdateMedicationResult:
    course = await update_medication_attribute(
        session,
        profile_id,
        medication_id,
        attribute,
        new_value,
    )
    return UpdateMedicationResult(updated=course is not None, course=course)


async def delete_course(
    session: AsyncSession,
    *,
    profile_id: int,
    medication_id: int,
) -> DeleteMedicationResult:
    deleted = await delete_medication(session, profile_id, medication_id)
    return DeleteMedicationResult(deleted=deleted)
