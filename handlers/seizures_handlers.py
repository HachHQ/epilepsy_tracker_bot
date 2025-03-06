from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from services.update_login_cache import get_cached_login
from database.models import User, Profile
from keyboards.menu_kb import get_main_menu_keyboard
from keyboards.seizure_kb import get_year_date_kb, get_profiles_for_seizure_fix, get_month_date_kb


seizures_router = Router()

class SeizureForm(StatesGroup):
    date = State()
    year = State()
    month = State()
    hour = State()
    minutes_range = State()
    count = State()
    triggers = State()
    severity = State()
    duration = State()
    comment = State()
    symptoms = State()
    video_tg_id = State()
#     created_at =
#     updated_at =
#     location =

@seizures_router.callback_query(F.data.startswith("back"))
async def back_to(callback: CallbackQuery, state: FSMContext):
    _, back_to_target = callback.data.split(":", 1)

    if back_to_target == "to_menu":
        redis_login = await get_cached_login(callback.message.chat.id)
        await callback.message.edit_text(
            f"Логин: {redis_login}\n"
            f"Вы находитесь в основном меню бота.\n"
            "Используйте кнопки для навигации.\n",
            reply_markup=get_main_menu_keyboard()
        )
    elif back_to_target == "year":
        data = await state.get_data()
        await callback.message.edit_text(f"Выбран профиль - {data['profile_name']}\nВыберите год или сразу день из преложенных",
                                            reply_markup=get_year_date_kb(3,1))
        return
    await state.clear()
    await callback.answer()

@seizures_router.callback_query(F.data == "menu:choose_profile")
async def offer_to_choose_profile(callback: CallbackQuery, db: AsyncSession):
    redis_login = await get_cached_login(callback.message.chat.id)
    try:
        query = (
            select(Profile)
            .join(User)
            .where(User.login == redis_login)
        )
        profiles_result = await db.execute(query)
        profiles = profiles_result.scalars().all()
        await callback.message.edit_text("Выберите профиль для которого хотите зафиксировать приступ: ", reply_markup=get_profiles_for_seizure_fix(profiles))
    except SQLAlchemyError as e:
        print(f"Ошибка при выполнении запроса: {e}")
        await callback.answer()

@seizures_router.callback_query(F.data.startswith("fix_seizure"))
async def start_fix_seizure(callback: CallbackQuery, state: FSMContext):
    print("не кнопка назад")
    _, profile_id, profile_name = callback.data.split(":", 2)
    await state.update_data(profile_id=profile_id)
    await state.update_data(profile_name=profile_name)
    await callback.message.answer(f"Выбран профиль - {profile_name}\nВыберите год или сразу день из преложенных",
                                        reply_markup=get_year_date_kb(3,1))
    await callback.answer()

@seizures_router.callback_query(F.data.startswith("year"))
async def process_date_short(callback: CallbackQuery, state: FSMContext):
    _, year = callback.data.split(":", 1)
    if year == "two_d_ago":
        await state.update_data(date_short=year)
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text()
        return
    elif year == "one_d_ago":
        await state.update_data(date_short=year)
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text()
        return
    elif year == "today":
        await state.update_data(date_short=year)
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text()
        return
    else:
        await state.update_data(year=year)
        await state.set_state(SeizureForm.month)
        await callback.message.edit_text(f"Выбран {year} год.\nВыберите месяц:", reply_markup=get_month_date_kb())
