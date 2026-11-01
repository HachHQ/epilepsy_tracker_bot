from dataclasses import replace
from typing import TypedDict, Unpack

from middleware.oferta_gate import OfertaGateInput, command_name, decide_oferta_access


class _GateOverrides(TypedDict, total=False):
    has_user: bool
    is_oferta_accepted: bool
    is_deleted: bool
    is_start: bool
    is_accept: bool
    is_cancel: bool
    raw_state: str | None
    registration_unlocked: bool
    registration_step: bool
    is_restore_callback: bool


def _gate(**overrides: Unpack[_GateOverrides]) -> OfertaGateInput:
    return replace(
        OfertaGateInput(
            has_user=False,
            is_oferta_accepted=False,
            is_deleted=False,
            is_start=False,
            is_accept=False,
            is_cancel=False,
            raw_state=None,
            registration_unlocked=False,
            registration_step=False,
            is_restore_callback=False,
        ),
        **overrides,
    )


def test_command_name_strips_bot_mention() -> None:
    assert command_name("/start@epilepsy_bot") == "/start"
    assert command_name("/menu payload") == "/menu"
    assert command_name("обычный текст") is None
    assert command_name(None) is None


def test_new_user_without_acceptance_is_blocked() -> None:
    assert decide_oferta_access(_gate()) == "show_oferta"


def test_start_and_accept_are_allowed_before_registration() -> None:
    assert decide_oferta_access(_gate(is_start=True)) == "allow"
    assert decide_oferta_access(_gate(is_accept=True)) == "allow"


def test_registration_continues_only_after_accept_flag() -> None:
    blocked = _gate(raw_state="UserForm:name", registration_unlocked=False, registration_step=True)
    opened = _gate(raw_state="UserForm:login", registration_unlocked=True, registration_step=True)
    menu_during_form = _gate(raw_state="UserForm:login", registration_unlocked=True)
    assert decide_oferta_access(blocked) == "show_oferta"
    assert decide_oferta_access(opened) == "allow"
    assert decide_oferta_access(menu_during_form) == "continue_registration"


def test_cancel_is_allowed_inside_registration_form() -> None:
    gate = _gate(raw_state="UserForm:timezone", is_cancel=True)
    assert decide_oferta_access(gate) == "allow"


def test_existing_user_must_accept_before_menu() -> None:
    gate = _gate(has_user=True, is_oferta_accepted=False)
    assert decide_oferta_access(gate) == "show_oferta"
    assert decide_oferta_access(_gate(has_user=True, is_oferta_accepted=False, is_accept=True)) == "allow"


def test_accepted_user_can_use_the_bot() -> None:
    gate = _gate(has_user=True, is_oferta_accepted=True)
    assert decide_oferta_access(gate) == "allow"


def test_deleted_account_can_be_restored_only_after_acceptance() -> None:
    hidden = _gate(has_user=True, is_deleted=True, is_oferta_accepted=False)
    assert decide_oferta_access(hidden) == "show_oferta"
    assert decide_oferta_access(replace(hidden, is_start=True)) == "allow"
    accepted = replace(hidden, is_oferta_accepted=True)
    assert decide_oferta_access(accepted) == "show_deleted"
    assert decide_oferta_access(replace(accepted, is_start=True)) == "allow"
    assert decide_oferta_access(replace(accepted, is_restore_callback=True)) == "allow"
    assert (
        decide_oferta_access(replace(accepted, raw_state="AccountForm:restore_codeword"))
        == "allow"
    )
