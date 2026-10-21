from datetime import datetime

import pytz
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from timezonefinder import TimezoneFinder

from adapters.telegram.anchor import ANCHOR_MESSAGE_ID, live_message, send_anchor
from adapters.telegram.ephemeral import send_notice
from handlers.main_menu import return_to_main_menu, show_main_menu
from handlers_logic.states_factories import UserForm
from i18n import t
from keyboards.menu_kb import get_cancel_kb
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb, get_timezone_kb
from services.keyword_hasher import KeywordHasher
from services.profile_ref import ProfileRef
from services.redis_cache_data import get_cached_login
from services.validators import (
    validate_codeword,
    validate_login_of_user_form,
    validate_name_of_user_form,
    validate_timezone,
)
from use_cases.users import register_user_from_form

user_form_router = Router()


def _profile_offer_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data="to_filling_profile_form")
    builder.button(text=t("common.no"), callback_data="to_menu_edit")
    builder.adjust(2)
    return builder.as_markup()


def _registration_text(name: str, login: str) -> str:
    summary = t("user.registration_complete", name=name, login=login).rstrip()
    offer = t("user.offer_to_create_profile").strip()
    return f"{summary}\n\n{offer}"


async def _show_name_step(message: Message, state: FSMContext) -> None:
    await send_anchor(message, state, t("user.enter_username"), reply_markup=get_cancel_kb())
    await state.set_state(UserForm.name)


async def _show_timezone_step(message: Message, state: FSMContext) -> None:
    await send_anchor(
        message,
        state,
        t("user.timezone_info"),
        reply_markup=get_timezone_kb(),
        parse_mode="HTML",
    )
    await state.set_state(UserForm.timezone)


async def _show_codeword_step(message: Message, state: FSMContext) -> None:
    await send_anchor(message, state, t("user.codeword_prompt"), reply_markup=get_cancel_kb())
    await state.set_state(UserForm.code_word)


async def _show_login_step(message: Message, state: FSMContext) -> None:
    await send_anchor(message, state, t("user.enter_login"), reply_markup=get_cancel_kb())
    await state.set_state(UserForm.login)


async def _accept_timezone(message: Message, state: FSMContext, timezone: str) -> None:
    await state.update_data(timezone=timezone)
    await send_notice(
        message,
        t("user.timezone_detected", timezone=timezone),
        reply_markup=ReplyKeyboardRemove(),
    )
    await _show_codeword_step(message, state)


@user_form_router.callback_query(F.data == "submit_welcome_msg")
async def start_form(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    current_profile: ProfileRef | None,
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    user_is_exist = await get_cached_login(db, message.chat.id)
    if user_is_exist is not None:
        await state.clear()
        await show_main_menu(message, db, current_profile, edit=True)
        await callback.answer()
        return
    await message.edit_text(t("user.enter_username"), reply_markup=get_cancel_kb())
    await state.update_data({ANCHOR_MESSAGE_ID: message.message_id})
    await state.set_state(UserForm.name)
    await callback.answer()


@user_form_router.message(StateFilter(UserForm.name))
async def process_name(message: Message, state: FSMContext):
    if message.text and validate_name_of_user_form(message.text):
        await state.update_data(name=message.text)
        # The location button stays after this notice is deleted. The timezone step removes it.
        await send_notice(
            message,
            t("user.name_saved"),
            reply_markup=get_geolocation_for_timezone_kb(),
        )
        await _show_timezone_step(message, state)
        return
    await send_notice(message, t("user.invalid_name"))
    await _show_name_step(message, state)


@user_form_router.message(F.location, StateFilter(UserForm.timezone))
async def process_timezone_by_geolocation(message: Message, state: FSMContext):
    if message.location is None:
        await send_notice(
            message,
            t("user.timezone_not_found"),
            reply_markup=get_geolocation_for_timezone_kb(),
        )
        await _show_timezone_step(message, state)
        return
    tf = TimezoneFinder()
    latitude = message.location.latitude
    longitude = message.location.longitude
    timezone_name = tf.timezone_at(lat=latitude, lng=longitude)
    if not timezone_name:
        await send_notice(
            message,
            t("user.timezone_not_found"),
            reply_markup=get_geolocation_for_timezone_kb(),
        )
        await _show_timezone_step(message, state)
        return
    timezone = pytz.timezone(timezone_name)
    utc_offset = datetime.now(timezone).utcoffset()
    if utc_offset is None:
        await send_notice(
            message,
            t("user.timezone_not_found"),
            reply_markup=get_geolocation_for_timezone_kb(),
        )
        await _show_timezone_step(message, state)
        return
    tz_value = f"{int(utc_offset.total_seconds() / 3600):+}"
    await _accept_timezone(message, state, tz_value)


@user_form_router.callback_query(F.data.contains("timezone_"), StateFilter(UserForm.timezone))
async def process_timezone(callback: CallbackQuery, state: FSMContext):
    message = live_message(callback.message)
    if message is None or callback.data is None:
        await callback.answer()
        return
    timezone = callback.data.split("_", 1)[1]
    await _accept_timezone(message, state, timezone)
    await callback.answer()


@user_form_router.message(StateFilter(UserForm.timezone))
async def process_timezone_by_msg(message: Message, state: FSMContext):
    if message.text and validate_timezone(message.text):
        await _accept_timezone(message, state, message.text)
        return
    await send_notice(
        message,
        t("user.invalid_timezone"),
        reply_markup=get_geolocation_for_timezone_kb(),
    )
    await _show_timezone_step(message, state)


@user_form_router.message(StateFilter(UserForm.code_word))
async def process_codeword(message: Message, state: FSMContext):
    if message.text and validate_codeword(message.text):
        hasher = KeywordHasher()
        await state.update_data(codeword=hasher.hash_keyword(message.text))
        await _show_login_step(message, state)
        return
    await send_notice(message, t("user.codeword_invalid"))
    await _show_codeword_step(message, state)


@user_form_router.message(StateFilter(UserForm.login))
async def process_login(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    current_profile: ProfileRef | None,
):
    if not message.text or not validate_login_of_user_form(message.text):
        await send_notice(message, t("user.incorrect_login"))
        await _show_login_step(message, state)
        return

    await state.update_data(login=message.text)
    data = await state.get_data()
    result = await register_user_from_form(
        db,
        telegram_id=message.chat.id,
        telegram_username=message.from_user.username if message.from_user else None,
        telegram_fullname=message.from_user.full_name if message.from_user else None,
        form_data=data,
    )
    if result.reason == "telegram_id_exists":
        await return_to_main_menu(
            message,
            state,
            db,
            current_profile,
            notice=t("user.user_exist"),
        )
        return
    if result.reason == "account_deleted_restore_available":
        await send_anchor(message, state, t("user.account_deleted_restore_hint"))
        await state.clear()
        return
    if result.reason == "login_exists":
        await send_notice(message, t("user.login_exist"))
        await _show_login_step(message, state)
        return

    name = data.get("name")
    login = data.get("login")
    await send_anchor(
        message,
        state,
        _registration_text(str(name), str(login)),
        reply_markup=_profile_offer_kb(),
        parse_mode="HTML",
    )
    await state.clear()
