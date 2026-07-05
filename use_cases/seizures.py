from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Seizure
from database.repositories.seizures import (
    create_seizure,
    delete_seizure,
    normalize_feature_names,
    update_seizure_attribute,
)
from services.cache_invalidation import (
    invalidate_after_seizure_update,
    invalidate_seizure_caches,
)
from services.notes_formatters import get_minutes_and_seconds


@dataclass(frozen=True)
class SeizurePreview:
    seizure_id: int
    profile_name: str
    date: str
    time: str | None
    count: int | str | None
    triggers: str | None
    severity: str | None
    duration: str | None
    comment: str | None
    symptoms: str | None
    video_tg_id: str | None
    location: str | None
    type_of_seizure: str | None


def parse_current_profile(current_profile: str) -> tuple[int, str]:
    profile_id, profile_name = current_profile.split("|", 1)
    return int(profile_id), profile_name


def build_seizure_date(data: dict) -> str:
    if "date_short" in data:
        return data["date_short"]
    return (
        f"{data.get('year', 'Не заполнено')}-"
        f"{data.get('month', 'Не заполнено')}-"
        f"{data.get('day', 'Не заполнено')}"
    )


def build_location(data: dict) -> str | None:
    location = data.get("location")
    location_by_message = data.get("location_by_message")
    value = f"{location or ''}{location_by_message or ''}"
    return value or None


async def create_seizure_from_state(
    session: AsyncSession,
    *,
    user_id: int,
    current_profile: str,
    creator_login: str,
    state_data: dict,
) -> SeizurePreview:
    profile_id, profile_name = parse_current_profile(current_profile)
    manual_triggers = normalize_feature_names(state_data.get("triggers"))
    selected_triggers = normalize_feature_names(state_data.get("selected_triggers", []))
    trigger_names = selected_triggers + manual_triggers
    symptom_names = normalize_feature_names(state_data.get("symptoms"))
    date = build_seizure_date(state_data)
    location = build_location(state_data)

    seizure = await create_seizure(
        session,
        profile_id=profile_id,
        date=date,
        time=state_data.get("time_of_day"),
        severity=state_data.get("severity"),
        duration=state_data.get("duration"),
        comment=state_data.get("comment"),
        count=state_data.get("count"),
        video_tg_id=state_data.get("video_tg_id"),
        trigger_names=trigger_names,
        symptom_names=symptom_names,
        location=location,
        creator_login=creator_login,
        type_of_seizure=state_data.get("type_of_seizure"),
    )
    await invalidate_seizure_caches(user_id, profile_id)

    return SeizurePreview(
        seizure_id=seizure.id,
        profile_name=profile_name,
        date=date,
        time=seizure.time,
        count=seizure.count,
        triggers=", ".join(trigger_names) if trigger_names else None,
        severity=seizure.severity,
        duration=get_minutes_and_seconds(seizure.duration),
        comment=seizure.comment,
        symptoms=", ".join(symptom_names) if symptom_names else None,
        video_tg_id=seizure.video_tg_id,
        location=seizure.location,
        type_of_seizure=seizure.type_of_seizure,
    )


async def delete_seizure_record(
    session: AsyncSession,
    *,
    user_id: int,
    profile_id: int,
    seizure_id: int,
) -> bool:
    deleted = await delete_seizure(session, seizure_id, profile_id)
    if deleted:
        await invalidate_seizure_caches(user_id, profile_id)
    return deleted


async def update_seizure_field(
    session: AsyncSession,
    *,
    user_id: int,
    profile_id: int,
    seizure_id: int,
    attribute: str,
    new_value,
) -> Seizure | None:
    seizure = await update_seizure_attribute(
        session,
        seizure_id,
        profile_id,
        attribute,
        new_value,
    )
    if seizure is not None:
        await invalidate_after_seizure_update(user_id, profile_id, attribute)
    return seizure
