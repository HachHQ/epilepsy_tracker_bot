from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatType, MessageEntityType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Chat, Message, MessageEntity, Update

from middleware.delete_plain import DeletePlainMessageMiddleware, should_delete_plain_message


def _bind_delete(message: Message, delete: Any = None) -> Any:
    bound = AsyncMock() if delete is None else delete
    object.__setattr__(message, "delete", bound)
    return bound


def _message(
    text: str | None = "привет",
    *,
    chat_type: ChatType = ChatType.PRIVATE,
    command_at: int | None = None,
) -> Message:
    entities = None
    if command_at is not None and text is not None:
        entities = [
            MessageEntity(
                type=MessageEntityType.BOT_COMMAND,
                offset=command_at,
                length=text.index(" ") if " " in text[command_at:] else len(text) - command_at,
            )
        ]
    return Message.model_construct(
        message_id=1,
        date=datetime.now(),
        chat=Chat.model_construct(id=42, type=chat_type),
        text=text,
        entities=entities,
    )


@pytest.mark.asyncio
async def test_plain_private_message_outside_form_is_deleted() -> None:
    message = _message()
    deleted = _bind_delete(message)
    middleware = DeletePlainMessageMiddleware()
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, {"raw_state": None})

    assert result == "ok"
    handler.assert_awaited_once()
    deleted.assert_awaited_once()


@pytest.mark.asyncio
async def test_form_answer_is_kept() -> None:
    message = _message("Артур")
    deleted = _bind_delete(message)
    middleware = DeletePlainMessageMiddleware()

    await middleware(AsyncMock(), message, {"raw_state": "UserForm:name"})

    deleted.assert_not_awaited()


@pytest.mark.asyncio
async def test_command_outside_form_is_kept() -> None:
    message = _message("/help", command_at=0)
    deleted = _bind_delete(message)
    middleware = DeletePlainMessageMiddleware()

    await middleware(AsyncMock(), message, {"raw_state": None})

    deleted.assert_not_awaited()


def test_text_with_command_in_the_middle_is_deleted() -> None:
    message = _message("смотри /help", command_at=7)
    assert should_delete_plain_message(message, {"raw_state": None}) is True


@pytest.mark.asyncio
async def test_non_text_message_outside_form_is_deleted() -> None:
    message = _message(None)
    deleted = _bind_delete(message)
    middleware = DeletePlainMessageMiddleware()

    await middleware(AsyncMock(), message, {"raw_state": None})

    deleted.assert_awaited_once()


def test_group_message_is_kept() -> None:
    message = _message(chat_type=ChatType.GROUP)
    assert should_delete_plain_message(message, {"raw_state": None}) is False


def test_missing_fsm_state_is_kept() -> None:
    message = _message()
    assert should_delete_plain_message(message, {}) is False


@pytest.mark.asyncio
async def test_delete_runs_after_handler_and_survives_telegram_errors() -> None:
    message = _message()
    order: list[str] = []

    async def handler(event: object, data: dict[str, object]) -> str:
        order.append("handler")
        return "ok"

    async def fail_delete(**_kwargs: object) -> bool:
        order.append("delete")
        raise TelegramBadRequest(method=MagicMock(), message="message can't be deleted")

    _bind_delete(message, fail_delete)
    middleware = DeletePlainMessageMiddleware()

    result = await middleware(handler, message, {"raw_state": None})

    assert result == "ok"
    assert order == ["handler", "delete"]


@pytest.mark.asyncio
async def test_handler_failure_keeps_the_message() -> None:
    message = _message()
    deleted = _bind_delete(message)
    middleware = DeletePlainMessageMiddleware()
    handler = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await middleware(handler, message, {"raw_state": None})

    deleted.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_message_outside_form_is_deleted() -> None:
    message = _message("лишнее")
    deleted = _bind_delete(message)
    update = Update.model_construct(update_id=1, message=message)
    middleware = DeletePlainMessageMiddleware()

    await middleware(AsyncMock(return_value=None), update, {"raw_state": None})

    deleted.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_update_is_ignored() -> None:
    update = Update.model_construct(update_id=2, message=None)
    middleware = DeletePlainMessageMiddleware()
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, update, {"raw_state": None})

    assert result == "ok"
    handler.assert_awaited_once()
