from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.anchor import live_message
from i18n import t
from keyboards.profiles_list_kb import get_paginated_profiles_kb
from services.redis_cache_data import get_cached_profiles_list

pagination_router = Router()

@pagination_router.callback_query((F.data.startswith('prev')) | (F.data.startswith('next')))
async def handle_pagination(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    direction, page, profile_type = payload.split(':', 2)
    share = False
    if payload.endswith('share'):
        share = True
        profile_type = profile_type.split('|', 1)[0]
    else:
        pass
    page_number = int(page)
    profiles_redis = await get_cached_profiles_list(db, message.chat.id, profile_type)
    if not profiles_redis:
        await message.answer(t("pagination.profiles_not_found"))
        await callback.answer()
        return
    new_page = (
        max(0, page_number - 1) if direction == "prev" else min(len(profiles_redis) // 5, page_number + 1)
    )
    await message.edit_text(
        t("choose_profile.select_profile"),
        reply_markup=get_paginated_profiles_kb(
            profiles=profiles_redis,
            page=new_page,
            profile_type=profile_type,
            to_share=share
        )
    )
    await callback.answer()