from types import SimpleNamespace

from middleware.current_profile import chat_id_from_event


def test_chat_id_from_message_update():
    event = SimpleNamespace(callback_query=None, message=SimpleNamespace(chat=SimpleNamespace(id=42)))
    assert chat_id_from_event(event) == 42


def test_chat_id_from_callback_update():
    message = SimpleNamespace(chat=SimpleNamespace(id=7))
    event = SimpleNamespace(callback_query=SimpleNamespace(message=message), message=None)
    assert chat_id_from_event(event) == 7


def test_chat_id_from_bare_message():
    event = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=9)), chat=SimpleNamespace(id=9))
    assert chat_id_from_event(event) == 9


def test_chat_id_missing():
    assert chat_id_from_event(SimpleNamespace()) is None
