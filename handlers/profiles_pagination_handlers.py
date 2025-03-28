from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from services.redis_cache_data import get_cached_profiles_list
from keyboards.profiles_list_kb import get_paginated_profiles_kb

pagination_router = Router()

@pagination_router.callback_query((F.data.startswith('prev')) | (F.data.startswith('next')))
async def handle_pagination(callback: CallbackQuery, db: AsyncSession):
    direction, page, profile_type = callback.data.split(':', 2)
    share = False
    if callback.data.endswith('share'):
        share = True
        profile_type = profile_type.split('|', 1)[0]
    else:
        pass
    page = int(page)
    profiles_redis = await get_cached_profiles_list(db, callback.message.chat.id, profile_type)
    if not profiles_redis:
        await callback.message.answer("Ошибка: Список профилей не найден.")
        await callback.answer()
        return
    new_page = max(0, page - 1) if direction == "prev" else min(len(profiles_redis) // 5, page + 1)
    await callback.message.edit_text(
        "Выберите профиль:",
        reply_markup=get_paginated_profiles_kb(
            profiles=profiles_redis,
            page=new_page,
            profile_type=profile_type,
            to_share=share
        )
    )
    await callback.answer()