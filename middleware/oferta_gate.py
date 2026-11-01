"""Decide whether an update may reach bot handlers before the oferta is accepted."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OfertaDecision = Literal["allow", "show_oferta", "show_deleted", "continue_registration"]


@dataclass(frozen=True)
class OfertaGateInput:
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


def command_name(text: str | None) -> str | None:
    if not text or not text.startswith("/"):
        return None
    token = text.split(maxsplit=1)[0]
    return token.split("@", 1)[0]


def decide_oferta_access(gate: OfertaGateInput) -> OfertaDecision:
    """Registered users who already accepted the oferta pass through.

    Everyone else may only open /start, accept the document, finish the
    registration form that the accept button started, or restore a hidden
    account after acceptance.
    """
    raw_state = gate.raw_state or ""
    in_user_form = raw_state.startswith("UserForm:")
    in_registration = in_user_form and gate.registration_unlocked
    in_restore = raw_state == "AccountForm:restore_codeword"
    full_access = gate.has_user and gate.is_oferta_accepted and not gate.is_deleted

    if full_access:
        return "allow"

    if gate.has_user and gate.is_oferta_accepted and gate.is_deleted:
        if gate.is_start or gate.is_restore_callback or in_restore or (gate.is_cancel and in_restore):
            return "allow"
        return "show_deleted"

    if (
        gate.is_start
        or gate.is_accept
        or (in_registration and gate.registration_step)
        or (gate.is_cancel and in_user_form)
    ):
        return "allow"
    if in_registration:
        return "continue_registration"
    return "show_oferta"
