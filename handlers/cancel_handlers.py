from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command, StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from database.redis_query import (
    delete_redis_cached_login, delete_redis_cached_current_profile, delete_redis_cached_profiles_list, delete_redis_profile_triggers_list, delete_redis_trusted_persons
)
from lexicon.lexicon import LEXICON_RU
from services.redis_cache_data import get_cached_current_profile
from services.to_excel import export_seizures_to_excel

cancel_router = Router()

@cancel_router.message(Command(commands="cancel"), ~StateFilter(default_state))
async def cancel_form(message: Message, state: FSMContext):
    await message.answer(LEXICON_RU['cancel_script'], reply_markup=ReplyKeyboardRemove())
    await state.clear()

@cancel_router.message(Command(commands="cancel"), StateFilter(default_state))
async def cancel_outside_fsm(message: Message):
    await message.answer(LEXICON_RU['not_in_script'], reply_markup=ReplyKeyboardRemove())

@cancel_router.callback_query(F.data == "cancel_fsm_script", ~StateFilter(default_state))
async def cancel_fsm_script(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(LEXICON_RU['cancel_script'], reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await callback.answer()

@cancel_router.callback_query(F.data == "cancel_fsm_script", StateFilter(default_state))
async def cancel_fsm_script(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(LEXICON_RU['not_in_script'], reply_markup=ReplyKeyboardRemove())
    await callback.answer()

@cancel_router.message(F.text.lower().contains('clear_redis'))
async def test(message: Message, db: AsyncSession, bot: Bot):
    prof = await get_cached_current_profile(db, message.chat.id)
    await delete_redis_cached_profiles_list(message.chat.id, 'user_own')
    await delete_redis_cached_current_profile(message.chat.id)
    await delete_redis_cached_login(message.chat.id)
    await delete_redis_trusted_persons(message.chat.id)
    await delete_redis_profile_triggers_list(message.chat.id, int(prof.split('|')[0]))

    await message.answer(f"Success")
