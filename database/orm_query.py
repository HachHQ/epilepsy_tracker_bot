import math
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import (User, Profile, RequestStatus, TrustedPersonProfiles,
                              TrustedPersonRequest, Drug, Seizure, profile_drugs)


async def orm_get_user(session: AsyncSession, chat_id: int):
    result = await session.execute(select(User).filter(User.telegram_id == chat_id))
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