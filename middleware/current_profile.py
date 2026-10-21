from sqlalchemy.ext.asyncio import AsyncSession

from services.profile_ref import ProfileRef
from services.redis_cache_data import get_cached_current_profile


def chat_id_from_event(event: object) -> int | None:
    callback = getattr(event, "callback_query", None)
    if callback is not None:
        message = getattr(callback, "message", None)
        chat = getattr(message, "chat", None)
        if chat is not None:
            return chat.id

    for attr in ("message", "edited_message", "channel_post"):
        inner = getattr(event, attr, None)
        chat = getattr(inner, "chat", None)
        if chat is not None:
            return chat.id

    message = getattr(event, "message", None)
    chat = getattr(message, "chat", None) or getattr(event, "chat", None)
    if chat is not None:
        return chat.id
    return None


async def load_current_profile(session: AsyncSession, event: object) -> ProfileRef | None:
    chat_id = chat_id_from_event(event)
    if chat_id is None:
        return None
    return await get_cached_current_profile(session, chat_id)
