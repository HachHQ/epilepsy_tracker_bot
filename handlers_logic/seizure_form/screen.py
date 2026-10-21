from dataclasses import dataclass


@dataclass(frozen=True)
class FormScreen:
    text: str | None = None
    reply_markup: object | None = None
    edit: bool = False
    markup_only: bool = False
    parse_mode: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class FormTurn:
    screens: tuple[FormScreen, ...] = ()
    ack: bool = False


def answer(text: str, reply_markup: object | None = None, parse_mode: str | None = None) -> FormScreen:
    return FormScreen(text=text, reply_markup=reply_markup, parse_mode=parse_mode)


def edit(text: str, reply_markup: object | None = None, parse_mode: str | None = None) -> FormScreen:
    return FormScreen(text=text, reply_markup=reply_markup, edit=True, parse_mode=parse_mode)


def edit_markup(reply_markup: object) -> FormScreen:
    return FormScreen(markup_only=True, reply_markup=reply_markup)


def location(latitude: float, longitude: float) -> FormScreen:
    return FormScreen(latitude=latitude, longitude=longitude)


def turn(*screens: FormScreen, ack: bool = False) -> FormTurn:
    return FormTurn(screens=screens, ack=ack)
