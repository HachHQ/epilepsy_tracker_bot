from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from services.redis_cache_data import (
    get_cached_current_profile, get_cached_login, get_cached_profiles_list
)
from config_data.config import load_config

cfg = load_config('.env')

admin_ids: list[int] = cfg.tg_bot.admins

class EditCommandFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:

        if not message.text.startswith('/edit'):
            return False
        parts = message.text.split('_', 1)
        return len(parts) == 2 and parts[1].isdigit()

class IsAdmin(BaseFilter):
    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = admin_ids

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids

class ProfileIsSetCb(BaseFilter):
    async def __call__(self, callback: CallbackQuery, db: AsyncSession) -> bool:
        curr_profile = await get_cached_current_profile(db, callback.message.chat.id)
        if curr_profile is not None:
            return True
        else:
            await callback.message.answer("Выберите профиль, сейчас же!!!!!!.")
            await callback.answer()
            return False

class ProfileIsSetMsg(BaseFilter):
    async def __call__(self, message: Message, db: AsyncSession) -> bool:
        curr_profile = await get_cached_current_profile(db, message.chat.id)
        if curr_profile is not None:
            return True
        else:
            await message.answer("Выберите профиль, сейчас же!!!!!!.")
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