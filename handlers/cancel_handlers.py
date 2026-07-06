from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from filters.correct_commands import IsAdmin
from i18n import t
from services.cache_invalidation import invalidate_user_debug_cache
from services.redis_cache_data import get_cached_current_profile

cancel_router = Router()

@cancel_router.message(Command(commands="cancel"), ~StateFilter(default_state))
async def cancel_form(message: Message, state: FSMContext):
    await message.answer(t("common.cancel_script"), reply_markup=ReplyKeyboardRemove())
    await state.clear()

@cancel_router.message(Command(commands="cancel"), StateFilter(default_state))
async def cancel_outside_fsm(message: Message):
    await message.answer(t("common.not_in_script"), reply_markup=ReplyKeyboardRemove())

@cancel_router.callback_query(F.data == "cancel_fsm_script", ~StateFilter(default_state))
async def cancel_fsm_script(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(t("common.cancel_script"), reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await callback.answer()

@cancel_router.callback_query(F.data == "cancel_fsm_script", StateFilter(default_state))
async def cancel_fsm_script_outside_fsm(callback: CallbackQuery):
    await callback.message.answer(t("common.not_in_script"), reply_markup=ReplyKeyboardRemove())
    await callback.answer()

@cancel_router.message(F.text.lower().contains("clear_redis"), IsAdmin())
async def clear_redis_cache(message: Message, db: AsyncSession):
    prof = await get_cached_current_profile(db, message.chat.id)
    profile_id = int(prof.split("|")[0]) if prof else None
    await invalidate_user_debug_cache(message.chat.id, profile_id)

    await message.answer(t("admin.redis_cleared"))
