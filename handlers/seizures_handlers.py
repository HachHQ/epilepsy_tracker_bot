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
from keyboards.seizure_kb import get_year_date_kb


seizures_router = Router()

class SeizureForm(StatesGroup):
    date = State()
    time = State()
    triggers = State()
    severity = State()
    duration = State()
    comment = State()
#     count =
#     symptoms =

#     video_tg_id =
#     created_at =
#     updated_at =
#     location =

@seizures_router.callback_query(F.data.startswith("back"))
async def back_to(callback: CallbackQuery):
    _, back_to_target = callback.data.split(":", 1)

    if back_to_target == "to_menu":
        redis_login = await get_cached_login(callback.message.chat.id)
        await callback.message.edit_text(
            f"Логин: {redis_login}\n"
            f"Вы находитесь в основном меню бота.\n"
            "Используйте кнопки для навигации.\n",
            reply_markup=get_main_menu_keyboard()
        )
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

        back_btn = InlineKeyboardButton(text="⬅️ Назад", callback_data="back:to_menu")
        profiles_kb_bd = InlineKeyboardBuilder()
        i=0
        for profile in profiles:
            i += 1
            profiles_kb_bd.button(text=f"{i} - {profile.profile_name}", callback_data=f"fix_seizure:{profile.id}")
        profiles_kb_bd.adjust(1)
        profiles_kb_bd.row(back_btn, width=1)

        await callback.message.edit_text("Выберите профиль для которого хотите зафиксировать приступ: ", reply_markup=profiles_kb_bd.as_markup())
    except SQLAlchemyError as e:
        print(f"Ошибка при выполнении запроса: {e}")
        profiles = []
        await callback.answer()

#TODO set a kb to this handler with years
@seizures_router.callback_query(F.data.startswith("fix_seizure"))
async def start_fix_seizure(callback: CallbackQuery, state: FSMContext):
    _, profile_id = callback.data.split(":", 1)
    await state.update_data(profile_id=profile_id)

    await callback.message.edit_text(f"Выбран профиль - {profile_id}\nВыберите год или день из преложенных",
                                    reply_markup=get_year_date_kb(3,1))
