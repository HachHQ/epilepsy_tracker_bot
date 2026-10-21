from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.anchor import live_message
from i18n import t
from keyboards.profiles_list_kb import get_choosing_type_of_profiles_kb, get_paginated_profiles_kb
from services.redis_cache_data import get_cached_profiles_list
from use_cases.profiles import switch_current_profile

choose_profile_router = Router()

@choose_profile_router.callback_query(F.data == 'choose_profile')
async def process_choosing_profile(callback: CallbackQuery):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    await message.answer(
        t("choose_profile.select_type"),
        reply_markup=get_choosing_type_of_profiles_kb()
    )
    await callback.answer()

@choose_profile_router.callback_query(F.data.startswith('profile_type'))
async def select_own_profile(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    _, profile_type = payload.split(':', 1)

    profiles_redis = await get_cached_profiles_list(db, message.chat.id, profile_type)

    await message.edit_text(
        t("choose_profile.select_profile"),
        reply_markup=get_paginated_profiles_kb(
            profiles=profiles_redis or [],
            page=0,
            profile_type=profile_type
        )
    )
    await callback.answer()


@choose_profile_router.callback_query((F.data.startswith('select_profile')) & ~(F.data.endswith('|share')))
async def process_choosing_of_profile(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    _, profile_id, profile_name = payload.split(':', 2)
    result = await switch_current_profile(
        db,
        chat_id=message.chat.id,
        profile_id=int(profile_id),
        profile_name=profile_name,
    )
    if not result.switched:
        await message.answer(t("choose_profile.profile_not_found"))
    else:
        await message.edit_text(t("choose_profile.profile_selected", profile_name=profile_name))
    await callback.answer()
