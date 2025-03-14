from aiogram import Router, F
from aiogram.types import CallbackQuery

from services.redis_cache_data import set_cached_current_profile, get_cached_profiles_list
from keyboards.profiles_list_kb import get_choosing_type_of_profiles_kb, get_paginated_profiles_kb

choose_profile_router = Router()

@choose_profile_router.callback_query(F.data == 'choose_profile')
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.answer(
        "Выберите тип профиля для назначения по умолчанию: ",
        reply_markup=get_choosing_type_of_profiles_kb()
    )
    await callback.answer()

@choose_profile_router.callback_query(F.data.startswith('profile_type'))
async def select_own_profile(callback: CallbackQuery):
    _, profile_type = callback.data.split(':', 1)

    profiles_redis = await get_cached_profiles_list(callback.message.chat.id, profile_type)

    await callback.message.edit_text(
        "Выберите профиль:",
        reply_markup=get_paginated_profiles_kb(
            profiles=profiles_redis,
            page=0,
            profile_type=profile_type
        )
    )
    await callback.answer()


@choose_profile_router.callback_query((F.data.startswith('select_profile')) & ~(F.data.endswith('|share')))
async def process_choosing_of_profile(callback: CallbackQuery):
    _, profile_id, profile_name = callback.data.split(':', 2)
    await set_cached_current_profile(callback.message.chat.id, profile_id=profile_id, profile_name=profile_name)
    await callback.message.answer(f"Профиль {profile_name} выбран.")
    await callback.answer()