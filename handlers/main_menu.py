import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from services.redis_cache_data import get_cached_login, get_cached_current_profile
from keyboards.menu_kb import get_main_menu_keyboard

main_menu_router = Router()

@main_menu_router.message(Command(commands="menu"))
async def send_main_menu(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()

    lg = await get_cached_login(db, message.chat.id)
    curr_prof = await get_cached_current_profile(db, message.chat.id)

    print(lg, curr_prof)
    await message.answer(
        f"Логин\\: `{lg if lg is not None else "Не зарегистрирован"}`\n\n"
        f"Текущий профиль\\: `{curr_prof.split('|', 1)[1] if curr_prof is not None else "Не выбран"}`\n\n"
        f"Вы находитесь в основном меню бота\\.\n"
        f"Используйте кнопки для навигации\\.\n",
        reply_markup=get_main_menu_keyboard(),
        parse_mode='MarkDownV2'
    )

@main_menu_router.callback_query(F.data == "to_menu")
async def send_main_menu_callback(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()

    lg = await get_cached_login(db, callback.message.chat.id)
    curr_prof = await get_cached_current_profile(db, callback.message.chat.id)

    print(lg, curr_prof)
    await callback.message.answer(
        f"Логин\\: `{lg if lg is not None else "Не зарегистрирован"}`\n\n"
        f"Текущий профиль\\: `{curr_prof.split('|', 1)[1] if curr_prof is not None else "Не выбран"}`\n\n"
        f"Вы находитесь в основном меню бота\\.\n"
        f"Используйте кнопки для навигации\\.\n",
        reply_markup=get_main_menu_keyboard(),
        parse_mode='MarkDownV2'
    )
    await callback.answer()
