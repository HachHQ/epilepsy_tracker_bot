from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from services.redis_cache_data import (
    get_cached_current_profile, get_cached_login, get_cached_profiles_list, get_cached_trusted_persons_agrigated_data
)
from config_data.config import get_config

class EditCommandFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:

        if not message.text.startswith('/edit'):
            return False
        parts = message.text.split('_', 1)
        return len(parts) == 2 and parts[1].isdigit()

class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return False
        return message.from_user.id in get_config().tg_bot.admins

class ProfileIsSetCb(BaseFilter):
    async def __call__(self, callback: CallbackQuery, db: AsyncSession) -> bool:
        curr_profile = await get_cached_current_profile(db, callback.message.chat.id)
        if curr_profile is not None:
            return True
        else:
            await callback.message.answer("Выберите профиль.")
            await callback.answer()
            return False

class ProfileIsSetMsg(BaseFilter):
    async def __call__(self, message: Message, db: AsyncSession) -> bool:
        curr_profile = await get_cached_current_profile(db, message.chat.id)
        if curr_profile is not None:
            return True
        else:
            await message.answer("Выберите профиль.")
            return False

class UserOwnProfilesListExist(BaseFilter):
    async def __call__(self, callback: CallbackQuery, db: AsyncSession) -> bool:
        profiles_redis = await get_cached_profiles_list(db, callback.message.chat.id)
        if profiles_redis is not None:
            return True
        else:
            await callback.message.answer("У вас не собственных профилей, которыми вы можете поделиться.")
            await callback.answer()
            return False

# class CheckPermissionToEditCb(BaseFilter):
#     async def __call__(self, callback: CallbackQuery, db: AsyncSession) -> bool:
#         curr_profile = await get_cached_current_profile(db, callback.message.chat.id)
#         trusted = await get_cached_trusted_persons_agrigated_data(db, callback.message.chat.id)
#         if profiles_redis is not None:
#             return True
#         else:
#             await callback.message.answer("У вас не собственных профилей, которыми вы можете поделиться.")
#             await callback.answer()
#             return False

# class CheckPermissionToEditMsg(BaseFilter):
#     async def __call__(self, message: Message, db: AsyncSession) -> bool:
#         curr_profile = await get_cached_current_profile(db, message.chat.id)
#         if curr_profile is not None:
#             return True
#         else:
#             await message.answer("Выберите профиль, сейчас же!!!!!!.")
#             return False