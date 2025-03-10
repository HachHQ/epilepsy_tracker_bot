from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from database.models import User, Profile, TrustedPersonProfiles
from services.update_login_cache import get_cached_login
from keyboards.profiles_list_kb import get_choosing_type_of_profiles_kb, get_paginated_profils_kb

choose_profile_router = Router()

class PaginationFactory(CallbackData, prefix="page"):
    direction: str
    page: int
    profile_type: str

@choose_profile_router.message(Command('profile'))
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.answer("Выберите тип профиля для назначения по умолчанию: ", reply_markup=get_choosing_type_of_profiles_kb())

@choose_profile_router.callback_query(F.data.startswith('profile_type'))
async def select_own_profile(callback: CallbackQuery, db: AsyncSession):
    _, profile_type = callback.data.split(':', 1)
    redis_login = await get_cached_login(callback.message.chat.id)
    if callback.data == "trusted":
        query = (
                select(Profile)
                .join(User)
                .where(User.login == redis_login)
            )
        profiles_result = await db.execute(query)
        profiles = profiles_result.scalars().all()
        await callback.message.answer(
        "Выберите профиль:",
        reply_markup=get_paginated_profiles(
            profiles=profiles,
            profile_type="own"
        )
    )
    elif callback.data == "user_own":
        query = (
                select(Profile)
                .join(User)
                .where(User.login == redis_login)
            )
        profiles_result = await db.execute(query)
        profiles = profiles_result.scalars().all()
        await callback.message.answer(
            "Выберите профиль:",
            reply_markup=get_paginated_profiles(
                profiles=profiles,
                profile_type="own"
            )
        )

# @choose_profile_router.message(F.data.startswith('profile_type'))
# async def select_trusted_profile(callback: CallbackQuery, db: AsyncSession):
#     profiles = await get_trusted_profiles_from_db(message.from_user.id)
#     await state.update_data(trusted_profiles=profiles, current_trusted_page=0)
#     await message.answer(
#         "Выберите доверенное лицо:",
#         reply_markup=get_paginated_profiles(
#             profiles=profiles,
#             profile_type="trusted"
#         )
#     )
#     await state.set_state(TrustedProfileSelection.selecting)

@choose_profile_router.callback_query(PaginationFactory.filter())
async def handle_pagination(callback: CallbackQuery, callback_data: PaginationFactory, db: AsyncSession):
    if callback.data == "trusted":
        query = (
                select(TrustedPersonProfiles)
                .join(User)
                .where(User.login == redis_login)
            )
        trusted_profiles_result = await db.execute(query)
        trusted_profiles_list = profiles_result.scalars().all()
        await callback.message.answer(
        "Выберите профиль:",
        reply_markup=get_paginated_profiles(
            profiles=profiles,
            profile_type="own"
        )
    )
    elif callback.data == "user_own":
        query = (
                select(Profile)
                .join(User)
                .where(User.login == redis_login)
            )
        profiles_result = await db.execute(query)
        profiles_list = profiles_result.scalars().all()
        await callback.message.answer(
            "Выберите профиль:",
            reply_markup=get_paginated_profiles(
                profiles=profiles_list,
                profile_type="own"
            )
        )
    # Получаем данные из состояния
    data = await state.get_data()
    profiles = data.get(f"{callback_data.profile_type}_profiles", [])

    # Вычисляем новую страницу
    new_page = callback_data.page
    if callback_data.direction == "prev":
        new_page -= 1
    elif callback_data.direction == "next":
        new_page += 1

    # Обновляем сообщение
    await callback.message.edit_text(
        f"Выберите {'доверенное лицо' if callback_data.profile_type == 'trusted' else 'профиль'}:",
        reply_markup=get_paginated_profiles(
            profiles=profiles,
            page=new_page,
            profile_type=callback_data.profile_type
        )
    )
    await callback.answer()
