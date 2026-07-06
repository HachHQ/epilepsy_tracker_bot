from datetime import datetime

import pytz
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from timezonefinder import TimezoneFinder

from handlers_logic.states_factories import UserForm
from i18n import t
from keyboards.menu_kb import get_cancel_kb
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb, get_timezone_kb
from services.keyword_hasher import KeywordHasher
from services.redis_cache_data import get_cached_login
from services.validators import (
    validate_codeword,
    validate_login_of_user_form,
    validate_name_of_user_form,
    validate_timezone,
)
from use_cases.users import register_user_from_form

user_form_router = Router()

@user_form_router.callback_query(F.data == "submit_welcome_msg")
async def start_form(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    user_is_exist = await get_cached_login(db, callback.message.chat.id)
    if user_is_exist is not None:
        await state.clear()
        await callback.message.edit_text(t("start.already_registered"))
        await callback.answer()
        return
    await callback.message.answer(t("user.enter_username"), reply_markup=get_cancel_kb())
    await state.set_state(UserForm.name)
    await callback.answer()

@user_form_router.message(StateFilter(UserForm.name))
async def process_name(message: Message, state: FSMContext):
    if validate_name_of_user_form(message.text):
        await state.update_data(name=message.text)
        await message.answer(t("user.name_saved"), reply_markup=get_geolocation_for_timezone_kb())
        await message.answer(t("user.timezone_info"), reply_markup=get_timezone_kb(), parse_mode='MarkDownV2')
        await state.set_state(UserForm.timezone)
    else:
        await message.answer(t("user.invalid_name"), reply_markup=get_cancel_kb())
        return

@user_form_router.message(F.location, StateFilter(UserForm.timezone))
async def process_timezone_by_geolocation(message: Message, state: FSMContext):
    tf = TimezoneFinder()
    latitude = message.location.latitude
    longitude = message.location.longitude
    timezone_name = tf.timezone_at(lat=latitude, lng=longitude)
    if timezone_name:
        timezone = pytz.timezone(timezone_name)
        now = datetime.now(timezone)
        utc_offset_seconds = now.utcoffset().total_seconds()
        utc_offset_hours = utc_offset_seconds / 3600
        tz_value = f"{int(utc_offset_hours):+}"
        await state.update_data(timezone=tz_value)
        await message.answer(
            t("user.timezone_detected", timezone=tz_value),
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer(t("user.codeword_prompt"), reply_markup=get_cancel_kb())
        await state.set_state(UserForm.code_word)
    else:
        await message.answer(t("user.timezone_not_found"))


@user_form_router.callback_query(F.data.contains("timezone_"),
                                    StateFilter(UserForm.timezone))
async def process_timezone(callback: CallbackQuery, state: FSMContext):
    timezone = callback.data.split('_')[1]
    await state.update_data(timezone=timezone)
    await callback.message.answer(
        t("user.timezone_detected", timezone=timezone),
        reply_markup=ReplyKeyboardRemove(),
    )
    await callback.message.answer(t("user.codeword_prompt"), reply_markup=get_cancel_kb())
    await state.set_state(UserForm.code_word)
    await callback.answer()

@user_form_router.message(StateFilter(UserForm.timezone))
async def process_timezone_by_msg(message: Message, state: FSMContext):
    timezone = message.text
    if validate_timezone(timezone):
        await state.update_data(timezone=timezone)
        await message.answer(
            t("user.timezone_detected", timezone=timezone),
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer(t("user.codeword_prompt"), reply_markup=get_cancel_kb())
        await state.set_state(UserForm.code_word)
    else:
        await message.answer(t("user.invalid_timezone"), reply_markup=get_cancel_kb())

@user_form_router.message(StateFilter(UserForm.code_word))
async def process_codeword(message: Message, state: FSMContext):
    code_word = message.text
    if validate_codeword(code_word):
        hasher = KeywordHasher()
        hashed_codeword = hasher.hash_keyword(code_word)
        await state.update_data(codeword=hashed_codeword)
        await state.set_state(UserForm.login)
        await message.answer(t("user.enter_login"), reply_markup=get_cancel_kb())
    else:
        await message.answer(t("user.codeword_invalid"), reply_markup=get_cancel_kb())

@user_form_router.message(StateFilter(UserForm.login))
async def process_login(message: Message, state: FSMContext, db: AsyncSession):
    if validate_login_of_user_form(message.text):
        await state.update_data(login=message.text)
        data = await state.get_data()
        result = await register_user_from_form(
            db,
            telegram_id=message.chat.id,
            telegram_username=message.from_user.username,
            telegram_fullname=message.from_user.full_name,
            form_data=data,
        )
        if result.reason == "telegram_id_exists":
            await message.answer(t("user.user_exist"))
            await state.clear()
            return
        if result.reason == "account_deleted_restore_available":
            await message.answer(t("user.account_deleted_restore_hint"))
            await state.clear()
            return
        if result.reason == "login_exists":
            await message.answer(t("user.login_exist"), reply_markup=get_cancel_kb())
            return

        next_to_profile_form_kb_bd = InlineKeyboardBuilder()
        next_to_profile_form_kb_bd.button(
            text=t("common.yes"), callback_data="to_filling_profile_form"
        )
        next_to_profile_form_kb_bd.button(
            text=t("common.no"), callback_data="to_menu"
        )
        await message.answer(
            t("user.registration_complete", name=data["name"], login=data["login"]),
            parse_mode='HTML',
        )
        await message.answer(
            t("user.offer_to_create_profile"),
            reply_markup=next_to_profile_form_kb_bd.as_markup(),
        )
    else:
        await message.answer(t("user.incorrect_login"), reply_markup=get_cancel_kb())
        return
    await state.clear()
