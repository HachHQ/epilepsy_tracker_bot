from aiogram.types import TelegramObject
from aiogram import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict
from services.notification_queue import NotificationQueue
from sqlalchemy.ext.asyncio import AsyncSession


from aiogram.types import TelegramObject
from aiogram import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict
from services.notification_queue import NotificationQueue
from sqlalchemy.ext.asyncio import AsyncSession

class DatabaseSessionMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker: Callable[[], AsyncSession]):
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with self.sessionmaker() as session:
            data["db"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()

# class DatabaseSessionMiddleware(BaseMiddleware):
#     def __init__(self, sessionmaker: Callable[[], AsyncSession]):
#         self.sessionmaker = sessionmaker

#     async def __call__(
#         self,
#         handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#         event: TelegramObject,
#         data: Dict[str, Any]
#     ) -> Any:
#         async with self.sessionmaker() as session:
#             data["db"] = session
#             result = await handler(event, data)
#             await session.commit()
#             return result

# class DatabaseSessionMiddleware(BaseMiddleware):
#     def __init__(self, sessionmaker):
#         super().__init__()
#         self.sessionmaker = sessionmaker

#     async def __call__(self, handler, event, data):
#         async with self.sessionmaker() as session:
#             data["db"] = session
#             response = await handler(event, data)
#             await session.commit()
#             return response

class NotificationMiddleware(BaseMiddleware):
    def __init__(self, notification_queue: NotificationQueue):
        super().__init__()
        self.notification_queue = notification_queue

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["notification_queue"] = self.notification_queue
        return await handler(event, data)
