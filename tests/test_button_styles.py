from aiogram.enums import ButtonStyle

from keyboards.menu_kb import get_main_menu_keyboard
from keyboards.notification_kb import get_choose_sos_notify_mode_kb
from keyboards.seizure_kb import get_review_kb, get_stop_duration_kb


def _buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def test_back_is_blue_and_save_is_green():
    buttons = {button.callback_data: button for button in _buttons(get_review_kb(back=True))}
    assert buttons["seizure_back"].style == ButtonStyle.PRIMARY
    assert buttons["seizure_save"].style == ButtonStyle.SUCCESS
    assert buttons["cancel_fsm_script"].style is None


def test_stop_and_emergency_are_red():
    stop = _buttons(get_stop_duration_kb())[0]
    assert stop.callback_data == "stop_track_duration"
    assert stop.style == ButtonStyle.DANGER

    menu = {button.callback_data: button for button in _buttons(get_main_menu_keyboard())}
    assert menu["sos_notification"].style == ButtonStyle.DANGER
    assert menu["seizure_right_now"].style is None

    send = _buttons(get_choose_sos_notify_mode_kb())[0]
    assert send.style == ButtonStyle.DANGER
