import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from services.redis_cache_data import get_cached_login, get_cached_current_profile
from keyboards.menu_kb import get_main_menu_keyboard

main_menu_router = Router()

async def get_main_menu_text(session: AsyncSession, message: Message):
    lg = await get_cached_login(session, message.chat.id)
    curr_prof = await get_cached_current_profile(session, message.chat.id)
    text = (
        f"🆔 Логин\\: `{lg if lg is not None else "Не зарегистрирован"}`\n\n"
        f"👤 Текущий профиль\\: `{curr_prof.split('|', 1)[1] if curr_prof is not None else "Не выбран"}`"
    )
    return text

@main_menu_router.message(Command(commands="menu"))
async def send_main_menu(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    text = await get_main_menu_text(db, message)
    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='MarkDownV2'
    )

@main_menu_router.callback_query((F.data == "to_menu") | (F.data == "to_menu_edit"))
async def send_main_menu_callback(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    text = await get_main_menu_text(db, callback.message)

    if callback.data == "to_menu":
        await callback.message.answer(
            text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='MarkDownV2'
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='MarkDownV2'
        )
    await callback.answer()
