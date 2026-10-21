from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import MessageEntityType
from aiogram.exceptions import TelegramBadRequest

from middleware.delete_command import DeleteCommandMiddleware


def _menu_message() -> MagicMock:
    message = MagicMock()
    message.entities = [
        MagicMock(type=MessageEntityType.BOT_COMMAND, offset=0, length=5),
    ]
    message.text = "/menu"
    message.chat.id = 12345
    message.delete = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_delete_command_middleware_deletes_menu_after_success() -> None:
    message = _menu_message()
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, {})

    assert result == "ok"
    handler.assert_awaited_once()
    message.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_command_middleware_skips_non_configured_command() -> None:
    message = _menu_message()
    message.text = "/help"
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(return_value="ok")

    await middleware(handler, message, {})

    message.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_command_middleware_does_not_delete_on_handler_failure() -> None:
    message = _menu_message()
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(side_effect=RuntimeError("handler failed"))

    with pytest.raises(RuntimeError, match="handler failed"):
        await middleware(handler, message, {})

    message.delete.assert_not_awaited()


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
    message = _menu_message()
    message.delete = AsyncMock(side_effect=TelegramBadRequest(method="deleteMessage", message="forbidden"))
    middleware = DeleteCommandMiddleware()
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, {})

    assert result == "ok"
    message.delete.assert_awaited_once()
