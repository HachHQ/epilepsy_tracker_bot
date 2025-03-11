import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from database.redis_client import redis
from database.models import User, Profile, TrustedPersonProfiles
from services.update_login_cache import get_cached_login
from keyboards.profiles_list_kb import get_choosing_type_of_profiles_kb, get_paginated_profiles_kb

choose_profile_router = Router()

@choose_profile_router.message(Command('profile'))
async def process_choosing_profile(message: Message):
    await message.answer(
        "Выберите тип профиля для назначения по умолчанию: ",
        reply_markup=get_choosing_type_of_profiles_kb()
    )

@choose_profile_router.callback_query(F.data.startswith('profile_type'))
async def select_own_profile(callback: CallbackQuery, db: AsyncSession):
    _, profile_type = callback.data.split(':', 1)

    cache_key = f"profiles:{callback.message.chat.id}:{profile_type}"
    cached_profiles = await redis.get(cache_key)

    if cached_profiles:
        profiles = json.loads(cached_profiles.decode('utf-8'))
    else:
        if profile_type == "trusted":
            query = (
                select(Profile)
                .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
                .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
                .where(User.telegram_id == callback.message.chat.id)
            )
        elif profile_type == "user_own":
            redis_login = await get_cached_login(callback.message.chat.id)
            query = (
                select(Profile)
                .join(User)
                .where(User.login == redis_login)
            )
        else:
            await callback.message.answer("Неверный тип профиля.")
            return

        profiles_result = await db.execute(query)
        profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]

        await redis.setex(cache_key, 3600, json.dumps(profiles))

    await callback.message.edit_text(
        "Выберите профиль:",
        reply_markup=get_paginated_profiles_kb(
            profiles=profiles,
            page=0,
            profile_type=profile_type
        )
    )
    await callback.answer()

@choose_profile_router.callback_query((F.data.startswith('prev')) | (F.data.startswith('next')))
async def handle_pagination(callback: CallbackQuery):
    direction, page, profile_type = callback.data.split(':', 2)
    page = int(page)

    cache_key = f"profiles:{callback.message.chat.id}:{profile_type}"
    cached_profiles = await redis.get(cache_key)

    if not cached_profiles:
        await callback.message.answer("Ошибка: Список профилей не найден.")
        return

    profiles = json.loads(cached_profiles.decode('utf-8'))

    new_page = max(0, page - 1) if direction == "prev" else min(len(profiles) // 5, page + 1)

    await callback.message.edit_text(
        "Выберите профиль:",
        reply_markup=get_paginated_profiles_kb(
            profiles=profiles,
            page=new_page,
            profile_type=profile_type
        )
    )
    await callback.answer()