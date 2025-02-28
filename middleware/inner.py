from aiogram.types import Message
from aiogram.types import TelegramObject
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict
from services.notification_queue import NotificationQueue


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
        data["notification_queue"] = self.notification_queue  # Добавляем в data
        return await handler(event, data)