from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatType, MessageEntityType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Chat, Message, MessageEntity

from middleware.delete_command import DeleteCommandMiddleware


def _command_message(text: str, delete: Any = None) -> tuple[Message, Any]:
    command = text.split()[0]
    message = Message.model_construct(
        message_id=1,
        date=datetime.now(),
        chat=Chat.model_construct(id=12345, type=ChatType.PRIVATE),
        text=text,
        entities=[
            MessageEntity(
                type=MessageEntityType.BOT_COMMAND,
                offset=0,
                length=len(command),
            )
        ],
    )
    bound = AsyncMock() if delete is None else delete
    object.__setattr__(message, "delete", bound)
    return message, bound


@pytest.mark.asyncio
async def test_delete_command_middleware_deletes_menu_after_success() -> None:
    message, deleted = _command_message("/menu")
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, {})

    assert result == "ok"
    handler.assert_awaited_once()
    deleted.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_command_middleware_skips_non_configured_command() -> None:
    message, deleted = _command_message("/help")
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(return_value="ok")

    await middleware(handler, message, {})

    deleted.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_command_middleware_does_not_delete_on_handler_failure() -> None:
    message, deleted = _command_message("/menu")
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(side_effect=RuntimeError("handler failed"))

    with pytest.raises(RuntimeError, match="handler failed"):
        await middleware(handler, message, {})

    deleted.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_command_middleware_ignores_non_message_events() -> None:
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(return_value="ok")
    update = MagicMock()

    result = await middleware(handler, update, {})

    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_command_middleware_ignores_telegram_delete_errors() -> None:
    message, deleted = _command_message(
        "/menu",
        delete=AsyncMock(
            side_effect=TelegramBadRequest(method=MagicMock(), message="forbidden")
        ),
    )
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, {})

    assert result == "ok"
    deleted.assert_awaited_once()
