from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, KeyboardButton

from lexicon.lexicon import LEXICON_BUTTONS

cancel_btn = InlineKeyboardButton(text=LEXICON_BUTTONS['cancel'], callback_data="cancel_fsm_script")

def get_ask_for_have_diagnosis_kb() -> InlineKeyboardMarkup:
    epilepsy_types_kb_bd = InlineKeyboardBuilder()
    epilepsy_types_kb_bd.button(text="Да",
                                callback_data="have_epilepsy_diagnosis")
    epilepsy_types_kb_bd.button(text="Нет",
                                callback_data="dont_have_epilepsy_diagnosis")
    epilepsy_types_kb_bd.adjust(2)
    epilepsy_types_kb_bd.row(cancel_btn, width=1)
    return epilepsy_types_kb_bd.as_markup()

def get_sex_kb() -> InlineKeyboardMarkup:
    sex_kb_bd = InlineKeyboardBuilder()
    sex_kb_bd.button(text=LEXICON_BUTTONS['male'], callback_data="sex_male")
    sex_kb_bd.button(text=LEXICON_BUTTONS['female'], callback_data="sex_female")
    sex_kb_bd.adjust(2)
    sex_kb_bd.row(cancel_btn, width=1)
    return sex_kb_bd.as_markup()

def get_timezone_kb() -> InlineKeyboardMarkup:
    timezone_kb_bd = InlineKeyboardBuilder()
    [timezone_kb_bd.button(text=f"+{str(number)}", callback_data=f"timezone_+{number}") for number in range(11)]
    timezone_kb_bd.adjust(3)
    timezone_kb_bd.row(cancel_btn, width=1)
    return timezone_kb_bd.as_markup()

def get_geolocation_for_timezone_kb() -> ReplyKeyboardMarkup:
    send_geo_kb_bd = ReplyKeyboardBuilder()
    send_geolocation_btn = KeyboardButton(text=LEXICON_BUTTONS['send_geolocation'], request_location=True)
    send_geo_kb_bd.row(send_geolocation_btn, width=1)
    return send_geo_kb_bd.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_submit_profile_settings_kb() -> InlineKeyboardMarkup:
    submit_kb_bd = InlineKeyboardBuilder()
    submit_kb_bd.button(text=LEXICON_BUTTONS['submit'], callback_data="submit_profile_settings")
    submit_kb_bd.row(cancel_btn, width=1)
    return submit_kb_bd.as_markup()

def get_qeustion_about_species():
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="profile_for_human")
    builder.button(text="Нет", callback_data="profile_for_animal")
    builder.adjust(2)
    builder.row(cancel_btn, width=1)
    return builder.as_markup()