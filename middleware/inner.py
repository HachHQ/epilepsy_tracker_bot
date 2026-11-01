import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.notification_queue import NotificationQueue
from adapters.telegram.oferta import send_oferta_document
from i18n import t
from middleware.current_profile import load_current_profile
from middleware.oferta_gate import OfertaGateInput, command_name, decide_oferta_access
from use_cases.users import get_oferta_account_state

logger = logging.getLogger(__name__)

class DatabaseSessionMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker: Callable[[], AsyncSession]):
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        async with self.sessionmaker() as session:
            data["db"] = session
            data["current_profile"] = await load_current_profile(session, event)
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                logger.exception("Database session was rolled back after handler failure")
                raise

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

class OfertaGateMiddleware(BaseMiddleware):
    """Block bot features until the user accepts the oferta PDF."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)

        chat_id = _private_chat_id(event)
        if chat_id is None:
            return await handler(event, data)

        account = await get_oferta_account_state(data["db"], chat_id)
        raw_state = data.get("raw_state")
        registration_unlocked = await _registration_unlocked(data, raw_state)
        message_text = _message_text(event)
        callback_data = event.callback_query.data if event.callback_query else None
        command = command_name(message_text)
        raw = str(raw_state) if raw_state else ""
        decision = decide_oferta_access(
            OfertaGateInput(
                has_user=account.exists,
                is_oferta_accepted=account.is_oferta_accepted,
                is_deleted=account.is_deleted,
                is_start=command == "/start",
                is_accept=callback_data == "accept_oferta",
                is_cancel=command == "/cancel" or callback_data == "cancel_fsm_script",
                raw_state=raw or None,
                registration_unlocked=registration_unlocked,
                registration_step=_is_registration_step(
                    raw_state=raw,
                    registration_unlocked=registration_unlocked,
                    command=command,
                    callback_data=callback_data,
                ),
                is_restore_callback=callback_data == "account_restore_start",
            )
        )

        full_access = account.exists and account.is_oferta_accepted and not account.is_deleted
        if decision == "allow" and command == "/start" and not full_access:
            await _clear_state(data)

        if decision == "continue_registration":
            await data["bot"].send_message(chat_id, t("start.finish_registration"))
            await _answer_callback(event)
            return None

        if decision == "show_oferta":
            await _clear_state(data, keep_user_form=registration_unlocked)
            await send_oferta_document(data["bot"], chat_id, with_accept_button=True)
            await _answer_callback(event, t("start.oferta_required_alert"))
            return None

        if decision == "show_deleted":
            await _clear_state(data, keep_restore=True)
            await data["bot"].send_message(chat_id, t("start.deleted_use_start"))
            await _answer_callback(event)
            return None

        return await handler(event, data)


async def _registration_unlocked(data: dict[str, Any], raw_state: object) -> bool:
    if not raw_state or not str(raw_state).startswith("UserForm:"):
        return False
    state: FSMContext | None = data.get("state")
    if state is None:
        return False
    fsm_data = await state.get_data()
    return bool(fsm_data.get("oferta_accepted"))


async def _clear_state(
    data: dict[str, Any],
    *,
    keep_user_form: bool = False,
    keep_restore: bool = False,
) -> None:
    state: FSMContext | None = data.get("state")
    raw_state = data.get("raw_state")
    if state is None or not raw_state:
        return
    raw = str(raw_state)
    if keep_user_form and raw.startswith("UserForm:"):
        return
    if keep_restore and raw == "AccountForm:restore_codeword":
        return
    await state.clear()
    data["raw_state"] = None


def _is_registration_step(
    *,
    raw_state: str,
    registration_unlocked: bool,
    command: str | None,
    callback_data: str | None,
) -> bool:
    if not registration_unlocked or not raw_state.startswith("UserForm:"):
        return False
    if callback_data is None and command is None:
        return True
    if callback_data is None:
        return False
    return callback_data == "cancel_fsm_script" or callback_data.startswith("timezone_")


def _private_chat_id(update: Update) -> int | None:
    message = update.message or update.edited_message
    if message is not None:
        if message.chat.type != "private":
            return None
        return message.chat.id
    callback = update.callback_query
    if callback is None:
        return None
    if callback.message is not None and callback.message.chat.type == "private":
        return callback.message.chat.id
    if callback.message is None and callback.from_user is not None:
        return callback.from_user.id
    return None


def _message_text(update: Update) -> str | None:
    message = update.message or update.edited_message
    if message is None:
        return None
    return message.text


async def _answer_callback(update: Update, text: str | None = None) -> None:
    if update.callback_query is None:
        return
    await update.callback_query.answer(text)


class NotificationMiddleware(BaseMiddleware):
    def __init__(self, notification_queue: NotificationQueue):
        super().__init__()
        self.notification_queue = notification_queue

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        data["notification_queue"] = self.notification_queue
        return await handler(event, data)
