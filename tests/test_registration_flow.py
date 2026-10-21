import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardRemove

from adapters.telegram.anchor import ANCHOR_MESSAGE_ID
from adapters.telegram.ephemeral import NOTICE_TTL_SECONDS, send_notice
from handlers.cancel_handlers import cancel_form, cancel_fsm_script
from handlers.main_menu import show_main_menu
from handlers.user_form import (
    process_codeword,
    process_login,
    process_name,
    process_timezone,
    process_timezone_by_geolocation,
    process_timezone_by_msg,
    start_form,
)
from handlers_logic.states_factories import UserForm
from i18n import t
from use_cases.users import RegisterUserResult


class MemoryState:
    def __init__(self) -> None:
        self.storage: dict[str, object] = {}
        self.current: object = None
        self.cleared = 0

    async def get_data(self) -> dict[str, object]:
        return self.storage

    async def update_data(
        self, data: dict[str, object] | None = None, **kwargs: object
    ) -> None:
        if data:
            self.storage.update(data)
        self.storage.update(kwargs)

    async def set_state(self, value: object) -> None:
        self.current = value

    async def clear(self) -> None:
        self.storage.clear()
        self.current = None
        self.cleared += 1


class FakeMessage:
    def __init__(self, text: str | None = None, message_id: int = 10) -> None:
        self.text = text
        self.message_id = message_id
        self.chat = SimpleNamespace(id=42)
        self.from_user = SimpleNamespace(username="art", full_name="Art")
        self.location: object = None
        self.bot = SimpleNamespace(delete_message=AsyncMock())
        self.sent: list[FakeMessage] = []
        self.edits: list[dict[str, object]] = []
        self.reply_markup: object = None
        self.parse_mode: str | None = None
        self._next_id = 100
        self.delete: AsyncMock = AsyncMock()

    async def answer(
        self,
        text: str,
        reply_markup: object = None,
        parse_mode: str | None = None,
    ) -> "FakeMessage":
        sent = FakeMessage(text=text, message_id=self._next_id)
        self._next_id += 1
        sent.reply_markup = reply_markup
        sent.parse_mode = parse_mode
        sent._next_id = self._next_id
        self.sent.append(sent)
        return sent

    async def edit_text(
        self,
        text: str,
        reply_markup: object = None,
        parse_mode: str | None = None,
    ) -> None:
        self.text = text
        self.reply_markup = reply_markup
        self.parse_mode = parse_mode
        self.edits.append(
            {"text": text, "reply_markup": reply_markup, "parse_mode": parse_mode}
        )


def _callback(message: FakeMessage, data: str = "submit_welcome_msg") -> SimpleNamespace:
    return SimpleNamespace(message=message, data=data, answer=AsyncMock())


def _callbacks(markup: object) -> list[str]:
    keyboard = cast(InlineKeyboardMarkup, markup)
    return [button.callback_data or "" for row in keyboard.inline_keyboard for button in row]


@pytest.fixture(autouse=True)
async def _settle_notices(monkeypatch: pytest.MonkeyPatch):
    async def fast_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr("adapters.telegram.ephemeral.asyncio.sleep", fast_sleep)
    yield
    from adapters.telegram.ephemeral import _pending

    if _pending:
        await asyncio.gather(*list(_pending))


async def test_notice_deletes_itself_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []

    async def remember_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("adapters.telegram.ephemeral.asyncio.sleep", remember_sleep)
    message = FakeMessage()
    await send_notice(cast(Message, message), t("user.name_saved"))
    from adapters.telegram.ephemeral import _pending

    await asyncio.gather(*list(_pending))
    message.sent[0].delete.assert_awaited_once()
    assert delays == [NOTICE_TTL_SECONDS]


async def test_start_form_edits_welcome_into_name_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("handlers.user_form.get_cached_login", AsyncMock(return_value=None))
    message = FakeMessage(message_id=7)
    state = MemoryState()

    await start_form(_callback(message), state, AsyncMock(), None)
    assert message.text == t("user.enter_username")
    assert "1 до 20" in message.text
    assert state.storage[ANCHOR_MESSAGE_ID] == 7
    assert state.current == UserForm.name
    assert message.sent == []


async def test_start_form_opens_menu_for_registered_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("handlers.user_form.get_cached_login", AsyncMock(return_value="artur"))
    monkeypatch.setattr("handlers.main_menu.get_cached_login", AsyncMock(return_value="artur"))
    message = FakeMessage(message_id=7)
    state = MemoryState()

    await start_form(_callback(message), state, AsyncMock(), None)
    assert state.cleared == 1
    assert message.parse_mode == "MarkDownV2"
    assert "artur" in str(message.text)
    assert message.sent == []


async def test_valid_name_replaces_prompt_and_flashes_confirmation() -> None:
    message = FakeMessage(text="Артур")
    state = MemoryState()
    state.storage[ANCHOR_MESSAGE_ID] = 7

    await process_name(message, state)
    message.bot.delete_message.assert_awaited_once_with(chat_id=42, message_id=7)
    assert message.sent[0].text == t("user.name_saved")
    assert message.sent[1].text == t("user.timezone_info")
    assert message.sent[1].parse_mode == "HTML"
    assert state.storage["name"] == "Артур"
    assert state.storage[ANCHOR_MESSAGE_ID] == message.sent[1].message_id
    assert state.current == UserForm.timezone


async def test_invalid_name_restores_prompt_below_the_error() -> None:
    message = FakeMessage(text="Arthur123")
    state = MemoryState()
    state.storage[ANCHOR_MESSAGE_ID] = 7

    await process_name(message, state)
    assert message.sent[0].text == t("user.invalid_name")
    assert message.sent[1].text == t("user.enter_username")
    assert state.current == UserForm.name
    assert state.storage[ANCHOR_MESSAGE_ID] == message.sent[1].message_id


async def test_timezone_button_advances_to_codeword() -> None:
    message = FakeMessage(message_id=7)
    state = MemoryState()
    state.storage[ANCHOR_MESSAGE_ID] = 7

    await process_timezone(_callback(message, "timezone_+7"), state)
    assert state.storage["timezone"] == "+7"
    assert message.sent[0].text == t("user.timezone_detected", timezone="+7")
    assert isinstance(message.sent[0].reply_markup, ReplyKeyboardRemove)
    assert message.sent[1].text == t("user.codeword_prompt")
    assert "8 до 25" in str(message.sent[1].text)
    assert state.current == UserForm.code_word


async def test_invalid_timezone_keeps_the_step() -> None:
    message = FakeMessage(text="новосибирск")
    state = MemoryState()
    state.storage[ANCHOR_MESSAGE_ID] = 7

    await process_timezone_by_msg(message, state)
    assert message.sent[0].text == t("user.invalid_timezone")
    assert message.sent[1].text == t("user.timezone_info")
    assert state.current == UserForm.timezone


async def test_geolocation_stores_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    class Finder:
        def timezone_at(self, lat: float, lng: float) -> str:
            assert lat == 55.0
            assert lng == 82.9
            return "Asia/Novosibirsk"

    monkeypatch.setattr("handlers.user_form.TimezoneFinder", Finder)
    message = FakeMessage()
    message.location = SimpleNamespace(latitude=55.0, longitude=82.9)
    state = MemoryState()
    state.storage[ANCHOR_MESSAGE_ID] = 7

    await process_timezone_by_geolocation(message, state)
    assert state.storage["timezone"] == "+7"
    assert state.current == UserForm.code_word


async def test_invalid_codeword_keeps_rules_on_the_prompt() -> None:
    message = FakeMessage(text="short")
    state = MemoryState()
    state.storage[ANCHOR_MESSAGE_ID] = 7

    await process_codeword(message, state)
    assert message.sent[0].text == t("user.codeword_invalid")
    assert message.sent[1].text == t("user.codeword_prompt")
    assert state.current == UserForm.code_word


async def test_valid_codeword_asks_for_login(monkeypatch: pytest.MonkeyPatch) -> None:
    class Hasher:
        def hash_keyword(self, keyword: str) -> str:
            assert keyword == "secretword"
            return "hashed"

    monkeypatch.setattr("handlers.user_form.KeywordHasher", Hasher)
    message = FakeMessage(text="secretword")
    state = MemoryState()
    state.storage[ANCHOR_MESSAGE_ID] = 7

    await process_codeword(message, state)
    assert state.storage["codeword"] == "hashed"
    assert "6 до 25" in str(message.sent[0].text)
    assert state.current == UserForm.login


async def test_registration_ends_on_one_message_with_menu_button(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "handlers.user_form.register_user_from_form",
        AsyncMock(return_value=RegisterUserResult(created=True)),
    )
    message = FakeMessage(text="arthur_01")
    state = MemoryState()
    state.storage.update(name="Артур", timezone="+7", codeword="hashed", **{ANCHOR_MESSAGE_ID: 7})

    await process_login(message, state, AsyncMock(), None)
    screen = message.sent[0]
    assert "Анкета заполнена" in str(screen.text)
    assert "Хотите ли вы создать" in str(screen.text)
    assert screen.parse_mode == "HTML"
    assert _callbacks(screen.reply_markup) == ["to_filling_profile_form", "to_menu_edit"]
    assert state.cleared == 1
    assert len(message.sent) == 1


async def test_taken_login_returns_to_the_same_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "handlers.user_form.register_user_from_form",
        AsyncMock(return_value=RegisterUserResult(created=False, reason="login_exists")),
    )
    message = FakeMessage(text="arthur_01")
    state = MemoryState()
    state.storage.update(name="Артур", timezone="+7", codeword="hashed", **{ANCHOR_MESSAGE_ID: 7})

    await process_login(message, state, AsyncMock(), None)
    assert message.sent[0].text == t("user.login_exist")
    assert message.sent[1].text == t("user.enter_login")
    assert state.cleared == 0
    assert state.current == UserForm.login


async def test_existing_telegram_account_opens_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "handlers.user_form.register_user_from_form",
        AsyncMock(return_value=RegisterUserResult(created=False, reason="telegram_id_exists")),
    )
    monkeypatch.setattr("handlers.main_menu.get_cached_login", AsyncMock(return_value="artur"))
    message = FakeMessage(text="arthur_01")
    state = MemoryState()
    state.storage.update(name="Артур", timezone="+7", codeword="hashed", **{ANCHOR_MESSAGE_ID: 7})

    await process_login(message, state, AsyncMock(), None)
    assert message.sent[0].text == t("user.user_exist")
    assert message.sent[1].parse_mode == "MarkDownV2"
    message.bot.delete_message.assert_awaited_once_with(chat_id=42, message_id=7)
    assert state.cleared == 1


async def test_deleted_account_keeps_the_restore_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "handlers.user_form.register_user_from_form",
        AsyncMock(
            return_value=RegisterUserResult(
                created=False, reason="account_deleted_restore_available"
            )
        ),
    )
    message = FakeMessage(text="arthur_01")
    state = MemoryState()
    state.storage.update(name="Артур", timezone="+7", codeword="hashed", **{ANCHOR_MESSAGE_ID: 7})

    await process_login(message, state, AsyncMock(), None)
    assert message.sent[0].text == t("user.account_deleted_restore_hint")
    assert state.cleared == 1
    assert len(message.sent) == 1


async def test_cancel_during_registration_opens_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("handlers.main_menu.get_cached_login", AsyncMock(return_value=None))
    message = FakeMessage(message_id=7)
    state = MemoryState()
    state.storage[ANCHOR_MESSAGE_ID] = 7

    await cancel_fsm_script(_callback(message, "cancel_fsm_script"), state, AsyncMock(), None)
    assert message.sent[0].text == t("common.cancel_script")
    assert isinstance(message.sent[0].reply_markup, ReplyKeyboardRemove)
    assert message.sent[1].parse_mode == "MarkDownV2"
    message.bot.delete_message.assert_awaited_once_with(chat_id=42, message_id=7)
    assert state.cleared == 1


async def test_cancel_without_anchor_does_not_send_menu() -> None:
    message = FakeMessage()
    state = MemoryState()

    await cancel_form(message, state, AsyncMock(), None)
    assert message.sent[0].text == t("common.cancel_script")
    assert len(message.sent) == 1
    assert state.cleared == 1


async def test_menu_edit_falls_back_to_a_new_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("handlers.main_menu.get_cached_login", AsyncMock(return_value=None))
    message = FakeMessage()

    async def fail_edit(*_args: object, **_kwargs: object) -> None:
        raise TelegramBadRequest(
            method="editMessageText",  # type: ignore[arg-type]
            message="message can't be edited",
        )

    message.edit_text = fail_edit  # type: ignore[method-assign]

    await show_main_menu(cast(Message, message), AsyncMock(), None, edit=True)
    assert message.sent[0].parse_mode == "MarkDownV2"
