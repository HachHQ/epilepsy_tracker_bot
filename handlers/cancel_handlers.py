from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.anchor import ANCHOR_MESSAGE_ID, live_message
from filters.correct_commands import IsAdmin
from handlers.main_menu import return_to_main_menu
from i18n import t
from services.cache_invalidation import invalidate_user_debug_cache
from services.profile_ref import ProfileRef

cancel_router = Router()


async def _cancel_active_scenario(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    current_profile: ProfileRef | None,
) -> None:
    if (await state.get_data()).get(ANCHOR_MESSAGE_ID) is not None:
        await return_to_main_menu(
            message,
            state,
            db,
            current_profile,
            notice=t("common.cancel_script"),
        )
        return
    await message.answer(t("common.cancel_script"), reply_markup=ReplyKeyboardRemove())
    await state.clear()


@cancel_router.message(Command(commands="cancel"), ~StateFilter(default_state))
async def cancel_form(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    current_profile: ProfileRef | None,
):
    await _cancel_active_scenario(message, state, db, current_profile)


@cancel_router.message(Command(commands="cancel"), StateFilter(default_state))
async def cancel_outside_fsm(message: Message):
    await message.answer(t("common.not_in_script"), reply_markup=ReplyKeyboardRemove())


@cancel_router.callback_query(F.data == "cancel_fsm_script", ~StateFilter(default_state))
async def cancel_fsm_script(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    current_profile: ProfileRef | None,
):
    message = live_message(callback.message)
    if message is None:
        await state.clear()
        await callback.answer()
        return
    await _cancel_active_scenario(message, state, db, current_profile)
    await callback.answer()


@cancel_router.callback_query(F.data == "cancel_fsm_script", StateFilter(default_state))
async def cancel_fsm_script_outside_fsm(callback: CallbackQuery):
    message = live_message(callback.message)
    if message is not None:
        await message.answer(t("common.not_in_script"), reply_markup=ReplyKeyboardRemove())
    await callback.answer()

@cancel_router.message(F.text.lower().contains("clear_redis"), IsAdmin())
async def clear_redis_cache(message: Message, db: AsyncSession, current_profile: ProfileRef | None):
    prof = current_profile
    profile_id = prof.id if prof else None
    await invalidate_user_debug_cache(message.chat.id, profile_id)

    await message.answer(t("admin.redis_cleared"))
