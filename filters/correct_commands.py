from aiogram.filters import BaseFilter
from aiogram.types import Message

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