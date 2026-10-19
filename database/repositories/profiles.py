from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import retention_deadline
from database.models import MedicationCourse, Profile, Seizure, TrustedPersonProfiles, User
from database.repositories.trusted_persons import get_existing_trusted_link
from services.profile_access import profile_ref_for_viewer
from services.profile_ref import ProfileRef


async def create_profile(
    session: AsyncSession,
    *,
    user: User,
    profile_name: str,
    type_of_epilepsy: str | None,
    age: int,
    sex: str,
    biological_species: str | None,
) -> Profile:
    profile = Profile(
        user_id=user.id,
        profile_name=profile_name,
        type_of_epilepsy=type_of_epilepsy,
        age=age,
        sex=sex,
        biological_species=biological_species,
    )
    session.add(profile)
    await session.flush()
    return profile


async def get_profile_by_id(session: AsyncSession, profile_id: int) -> Profile | None:
    return await session.scalar(select(Profile).where(Profile.id == int(profile_id)))


async def get_active_profile_by_id(session: AsyncSession, profile_id: int) -> Profile | None:
    return await session.scalar(
        select(Profile).where(
            Profile.id == int(profile_id),
            Profile.deleted_at.is_(None),
        )
    )


async def list_user_profiles(session: AsyncSession, chat_id: int) -> list[dict]:
    result = await session.execute(
        select(Profile)
        .join(User)
        .where(User.telegram_id == chat_id, Profile.deleted_at.is_(None))
    )
    return [profile.to_dict() for profile in result.scalars().all()]


async def update_profile_attribute(
    session: AsyncSession,
    profile_id: int,
    attribute: str,
    new_value,
) -> Profile | None:
    profile = await get_active_profile_by_id(session, profile_id)
    if not profile:
        return None
    if not hasattr(profile, attribute):
        raise ValueError(f"Атрибут '{attribute}' не существует в модели Profile.")
    setattr(profile, attribute, new_value)
    return profile


async def _reassign_current_profile(session: AsyncSession, user: User, deleted_profile_id: int) -> None:
    if user.current_profile != deleted_profile_id:
        return
    replacement_id = await session.scalar(
        select(Profile.id)
        .where(
            Profile.user_id == user.id,
            Profile.deleted_at.is_(None),
            Profile.id != deleted_profile_id,
        )
        .limit(1)
    )
    user.current_profile = replacement_id


async def soft_delete_profile(session: AsyncSession, profile_id: int) -> int | None:
    """Mark profile deleted, preserve seizures, remove auxiliary profile data.

    Returns the number of preserved seizure records, or None if profile not found/already deleted.
    """
    profile = await get_active_profile_by_id(session, profile_id)
    if not profile:
        return None

    now = datetime.now(UTC)
    deadline = retention_deadline(from_time=now)

    preserved = await session.scalar(
        select(func.count()).select_from(Seizure).where(Seizure.profile_id == profile_id)
    )
    preserved = int(preserved or 0)
    if preserved:
        await session.execute(
            update(Seizure)
            .where(Seizure.profile_id == profile_id)
            .values(owner_user_id=profile.user_id, retention_until=deadline)
        )

    profile.deleted_at = now
    profile.seizures_retention_until = deadline

    await session.execute(
        delete(MedicationCourse).where(MedicationCourse.profile_id == profile_id)
    )
    await session.execute(
        delete(TrustedPersonProfiles).where(TrustedPersonProfiles.profile_id == profile_id)
    )

    user = await session.scalar(select(User).where(User.id == profile.user_id))
    if user:
        await _reassign_current_profile(session, user, profile_id)

    await session.flush()
    return preserved


async def delete_profile_by_id(session: AsyncSession, profile_id: int) -> bool:
    """Deprecated: use soft_delete_profile. Hard delete is intentionally unavailable."""
    preserved = await soft_delete_profile(session, profile_id)
    return preserved is not None


async def list_restorable_profiles(session: AsyncSession, chat_id: int) -> list[dict]:
    now = datetime.now(UTC)
    result = await session.execute(
        select(Profile)
        .join(User)
        .where(
            User.telegram_id == chat_id,
            Profile.deleted_at.is_not(None),
            Profile.seizures_retention_until.is_not(None),
            Profile.seizures_retention_until > now,
        )
    )
    return [profile.to_dict() for profile in result.scalars().all()]


async def get_restorable_profile_for_user(
    session: AsyncSession,
    *,
    chat_id: int,
    profile_id: int,
) -> Profile | None:
    now = datetime.now(UTC)
    return await session.scalar(
        select(Profile)
        .join(User)
        .where(
            User.telegram_id == chat_id,
            Profile.id == int(profile_id),
            Profile.deleted_at.is_not(None),
            Profile.seizures_retention_until.is_not(None),
            Profile.seizures_retention_until > now,
        )
    )


async def restore_profile(session: AsyncSession, profile_id: int) -> bool:
    profile = await get_profile_by_id(session, profile_id)
    if not profile or profile.deleted_at is None:
        return False

    now = datetime.now(UTC)
    if profile.seizures_retention_until and profile.seizures_retention_until < now:
        return False

    profile.deleted_at = None
    profile.seizures_retention_until = None

    await session.execute(
        update(Seizure)
        .where(Seizure.profile_id == profile_id)
        .values(owner_user_id=None, retention_until=None)
    )
    await session.flush()
    return True


async def get_user_current_active_profile(session: AsyncSession, chat_id: int) -> Profile | None:
    user = await session.scalar(
        select(User).where(User.telegram_id == chat_id, User.deleted_at.is_(None))
    )
    if not user or not user.current_profile:
        return None
    return await get_active_profile_by_id(session, user.current_profile)


async def resolve_profile_access(
    session: AsyncSession,
    user: User,
    profile_id: int,
) -> ProfileRef | None:
    profile = await get_active_profile_by_id(session, profile_id)
    if profile is None or profile.user_id is None:
        return None
    link = None
    if profile.user_id != user.id:
        link = await get_existing_trusted_link(
            session,
            trusted_person_user_id=user.id,
            profile_owner_id=profile.user_id,
            profile_id=profile.id,
        )
    return profile_ref_for_viewer(
        user.id,
        profile.user_id,
        profile.id,
        profile.profile_name,
        link_can_read=None if link is None else link.can_read,
        link_can_edit=None if link is None else link.can_edit,
    )


async def set_user_current_profile(
    session: AsyncSession,
    chat_id: int,
    profile_id: int,
) -> User | None:
    user = await session.scalar(
        select(User).where(User.telegram_id == chat_id, User.deleted_at.is_(None))
    )
    if not user:
        return None
    access = await resolve_profile_access(session, user, profile_id)
    if access is None:
        return None
    user.current_profile = access.id
    return user
