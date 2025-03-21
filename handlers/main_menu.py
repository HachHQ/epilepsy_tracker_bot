import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from services.redis_cache_data import get_cached_login, get_cached_current_profile
from keyboards.menu_kb import get_main_menu_keyboard

main_menu_router = Router()

@main_menu_router.message(Command(commands="menu"))
async def send_main_menu(message: Message):
    lg = await get_cached_login(message.chat.id)
    curr_prof = await get_cached_current_profile(message.chat.id)

    if curr_prof == "Не выбран":
        curr_prof = "Не выбран"
    else:
        curr_prof = curr_prof.split('|', 1)[1]
    print(lg)
    print(curr_prof)
    await message.answer(
        f"Логин: <u>{lg}</u>\n"
        f"Текущий профиль: <u>{curr_prof}</u>\n"
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )

@main_menu_router.callback_query(F.data == "to_menu")
async def send_main_menu_callback(callback: CallbackQuery):
    lg = await get_cached_login(callback.message.chat.id)
    curr_prof = await get_cached_current_profile(callback.message.chat.id)
    # print(curr_prof.split('|', 1)[1])
    if curr_prof == "Не выбран":
        curr_prof = "Не выбран"
    else:
        curr_prof = curr_prof.split('|', 1)[1]

    print(lg)
    print(curr_prof)
    await callback.message.answer(
        f"Логин: <u>{lg}</u>\n"
        f"Текущий профиль: <u>{curr_prof}</u>\n"
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()
