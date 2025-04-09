import math
from sqlalchemy import select, update, delete, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import (User, Profile, RequestStatus, TrustedPersonProfiles,
                              TrustedPersonRequest, Drug, Seizure, profile_drugs)


async def orm_get_user(session: AsyncSession, chat_id: int):
    result = await session.execute(select(User).filter(User.telegram_id == chat_id))
    user = result.scalars().first()
    return user

async def orm_get_user_by_login(session: AsyncSession, login: str):
    result = await session.execute(select(User).filter(User.login == login))
    user = result.scalars().first()
    return user

async def orm_get_current_profile_data(session: AsyncSession, chat_id: int):
    user = await orm_get_user(session, chat_id)
    if (not user) or (user.current_profile == None) :
        return None
    search_profile = await session.execute(select(Profile).filter(Profile.id == user.current_profile))
    profile = search_profile.scalars().first()
    if not profile:
        return None
    return profile

async def orm_get_profile_by_id(session: AsyncSession, profile_id: int):
    search_profile = await session.execute(select(Profile).filter(Profile.id == int(profile_id)))
    profile = search_profile.scalars().first()
    return profile

async def orm_get_trusted_profiles_list(session: AsyncSession, chat_id: int):
    query = (
            select(Profile)
            .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
            .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
            .where(User.telegram_id == chat_id)
        )
    profiles_result = await session.execute(query)
    profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
    return profiles

async def orm_get_user_own_profiles_list(session: AsyncSession, chat_id: int):
    query = (
            select(Profile)
            .join(User)
            .where(User.telegram_id == chat_id)
        )
    profiles_result = await session.execute(query)
    profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
    return profiles

async def orm_get_seizures_by_profile_ascending(session: AsyncSession, current_profile_id: int):
    query = (
            select(Seizure)
            .where(Seizure.profile_id == int(current_profile_id))
            .order_by(asc(Seizure.date))
        )
    seizures_result = await session.execute(query)
    return seizures_result.scalars().all()

async def orm_get_seizures_by_profile_descending(session: AsyncSession, current_profile_id: int):
    query = (
            select(Seizure)
            .where(Seizure.profile_id == int(current_profile_id))
            .order_by(desc(Seizure.date))
        )
    seizures_result = await session.execute(query)
    return seizures_result.scalars().all()

async def orm_get_seizure_info(session: AsyncSession, seizure_id: int, current_profile_id: int):
    query = (
        select(Seizure)
        .filter(
            (Seizure.profile_id == int(current_profile_id)),
            (Seizure.id == int(seizure_id))
        )
    )
    seizures_res = await session.execute(query)
    return seizures_res.scalars().first()

async def orm_delete_seizure(session: AsyncSession, seizure_id: int, current_profile_id: int) -> bool:
    query = (
        delete(Seizure)
        .where((Seizure.id == int(seizure_id)) & (Seizure.profile_id == int(current_profile_id)))
    )
    del_res = await session.execute(query)
    deleted_count = del_res.rowcount
    return deleted_count > 0

#Trusted person operations
async def orm_update_list_of_trusted_profiles(session: AsyncSession, chat_id: int):
    query = (
            select(Profile)
            .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
            .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
            .where(User.telegram_id == chat_id)
        )
    profiles_result = await session.execute(query)
    profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
    return profiles

# Create profile
async def orm_create_profile(
        session: AsyncSession,
        user_id,
        profile_name,
        type_of_epilepsy,
        age,
        sex,
        timezone,
        created_at
    ):
    new_profile = Profile(
            user_id=user_id,
            profile_name=profile_name,
            type_of_epilepsy=type_of_epilepsy,
            age=age,
            sex=sex,
            timezone=timezone,
            created_at=created_at
        )
    session.add(new_profile)

async def orm_add_new_seizure(
        session: AsyncSession,
        profile_id,
        date,
        time,
        severity,
        duration,
        comment,
        count,
        video_tg_id,
        triggers,
        location,
        symptoms
    ):
    new_seizure = Seizure(
        profile_id = profile_id,
        date = date,
        time = time if time else None,
        severity = severity if severity else None,
        duration = int(duration) if duration else None,
        comment = comment if comment else None,
        count = int(count) if count else None,
        video_tg_id = video_tg_id if video_tg_id else None,
        triggers = triggers if triggers else None,
        location = location if location else None,
        symptoms = symptoms if symptoms else None
    )
    session.add(new_seizure)

async def orm_update_seizure(session: AsyncSession, seizure_id: int, current_profile_id: int, attribute: str, new_value):
    query = (
        select(Seizure)
        .filter(
            (Seizure.profile_id == int(current_profile_id)),
            (Seizure.id == int(seizure_id))
        )
    )
    res = await session.execute(query)
    sz = res.scalars().first()
    if not sz:
        return None

    if hasattr(sz, attribute):
        setattr(sz, attribute, new_value)
    else:
        raise ValueError(f"Атрибут '{attribute}' не существует в модели Seizure.")
    return sz