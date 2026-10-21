from aiogram.types import CallbackQuery, Message

from i18n import t
from services.profile_ref import ProfileRef


async def deny_read_only(event: CallbackQuery | Message, profile: ProfileRef | None) -> bool:
    if profile is None or profile.can_edit:
        return False
    await _tell(event, "trusted.read_only")
    return True


async def deny_unless_owner(event: CallbackQuery | Message, profile: ProfileRef | None) -> bool:
    if profile is None or profile.is_owner:
        return False
    await _tell(event, "trusted.owner_only")
    return True


async def _tell(event: CallbackQuery | Message, key: str) -> None:
    text = t(key)
    if isinstance(event, CallbackQuery):
        if event.message is not None:
            await event.message.answer(text)
        await event.answer()
        return
    await event.answer(text)
