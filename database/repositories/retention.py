"""Scheduled and explicit purge of expired retention data."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    MedicationCourse,
    Profile,
    Seizure,
    TrustedPersonProfiles,
    TrustedPersonRequest,
    User,
    UserNotifications,
)
from database.repositories.seizures import delete_all_seizures_for_profile, delete_expired_seizures


@dataclass(frozen=True)
class RetentionPurgeStats:
    seizures_deleted: int = 0
    profiles_deleted: int = 0
    users_deleted: int = 0


async def hard_delete_profile_with_seizures(session: AsyncSession, profile_id: int) -> bool:
    profile = await session.scalar(select(Profile).where(Profile.id == int(profile_id)))
    if not profile:
        return False

    await delete_all_seizures_for_profile(session, profile_id)
    await session.execute(
        delete(MedicationCourse).where(MedicationCourse.profile_id == profile_id)
    )
    await session.execute(
        delete(TrustedPersonProfiles).where(TrustedPersonProfiles.profile_id == profile_id)
    )
    await session.execute(delete(Profile).where(Profile.id == profile_id))
    await session.flush()
    return True


async def purge_expired_profiles(session: AsyncSession, *, before: datetime) -> int:
    expired_profiles = await session.scalars(
        select(Profile.id).where(
            Profile.deleted_at.is_not(None),
            Profile.seizures_retention_until.is_not(None),
            Profile.seizures_retention_until < before,
        )
    )
    deleted = 0
    for profile_id in expired_profiles.all():
        remaining = await session.scalar(
            select(func.count()).select_from(Seizure).where(Seizure.profile_id == profile_id)
        )
        if int(remaining or 0) == 0:
            if await hard_delete_profile_with_seizures(session, profile_id):
                deleted += 1
    return deleted


async def purge_user_forever(session: AsyncSession, user_id: int) -> bool:
    user = await session.scalar(select(User).where(User.id == int(user_id)))
    if not user:
        return False

    profile_ids = await session.scalars(
        select(Profile.id).where(Profile.user_id == user.id)
    )
    for profile_id in profile_ids.all():
        await hard_delete_profile_with_seizures(session, profile_id)

    await session.execute(
        delete(TrustedPersonProfiles).where(
            (TrustedPersonProfiles.trusted_person_user_id == user.id)
            | (TrustedPersonProfiles.profile_owner_id == user.id)
        )
    )
    await session.execute(
        delete(TrustedPersonRequest).where(
            (TrustedPersonRequest.sender_id == user.id)
            | (TrustedPersonRequest.recepient_id == user.id)
        )
    )
    await session.execute(
        delete(UserNotifications).where(UserNotifications.user_id == user.id)
    )
    await session.execute(delete(User).where(User.id == user.id))
    await session.flush()
    return True


async def purge_profile_forever(
    session: AsyncSession,
    *,
    chat_id: int,
    profile_id: int,
) -> bool:
    profile = await session.scalar(
        select(Profile)
        .join(User)
        .where(
            User.telegram_id == chat_id,
            Profile.id == int(profile_id),
        )
    )
    if not profile:
        return False
    return await hard_delete_profile_with_seizures(session, profile_id)


async def purge_expired_users(session: AsyncSession, *, before: datetime) -> int:
    expired_users = await session.scalars(
        select(User.id).where(
            User.deleted_at.is_not(None),
            User.data_retention_until.is_not(None),
            User.data_retention_until < before,
        )
    )
    deleted = 0
    for user_id in expired_users.all():
        if await purge_user_forever(session, user_id):
            deleted += 1
    return deleted


async def purge_expired_data(session: AsyncSession) -> RetentionPurgeStats:
    now = datetime.now(UTC)
    seizures_deleted = await delete_expired_seizures(session, before=now)
    profiles_deleted = await purge_expired_profiles(session, before=now)
    users_deleted = await purge_expired_users(session, before=now)
    return RetentionPurgeStats(
        seizures_deleted=seizures_deleted,
        profiles_deleted=profiles_deleted,
        users_deleted=users_deleted,
    )
