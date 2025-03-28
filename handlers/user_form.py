from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import Command, StateFilter
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.models import User
from database.redis_query import set_redis_cached_login
from lexicon.lexicon import LEXICON_COMMANDS, LEXICON_RU
from services.validators import validate_login_of_user_form, validate_name_of_user_form
from keyboards.menu_kb import get_cancel_kb

user_form_router = Router()

class UserForm(StatesGroup):
    name = State()
    login = State()
    check_form = State()

@user_form_router.callback_query(F.data == "submit_welcome_msg")
async def start_form(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(LEXICON_RU['enter_username'], reply_markup=get_cancel_kb())
    await state.set_state(UserForm.name)
    await callback.answer()

@user_form_router.message(StateFilter(UserForm.name))
async def process_name(message: Message, state: FSMContext):
    if validate_name_of_user_form(message.text):
        print("Имя валидно")
        await state.update_data(name=message.text)
        await message.answer(LEXICON_RU['enter_login'], reply_markup=get_cancel_kb())
        await state.set_state(UserForm.login)
    else:
        await message.answer("Имя должно иметь длину от 1 до 20 символов, и использовать только буквы русского или английского алфавита", reply_markup=get_cancel_kb())
        return

@user_form_router.message(StateFilter(UserForm.login))
async def process_login(message: Message, state: FSMContext, db: AsyncSession):
    if validate_login_of_user_form(message.text):
        print("Логин валиден")
        await state.update_data(login=message.text)
        data = await state.get_data()
        print(f"Полученные данные: {data}")
        try:
            result = await db.execute(select(User).filter(User.login == data["login"]))
            existing_login = result.scalars().first()

            result = await db.execute(select(User).filter(User.telegram_id == message.chat.id))
            existing_tgid = result.scalars().first()

            if existing_tgid:
                await message.answer(LEXICON_RU['user_exist'])
                await state.clear()
                return
            if existing_login:
                await message.answer(LEXICON_RU['login_exist'], reply_markup=get_cancel_kb())
                return

            new_user = User(
                telegram_id=message.chat.id,
                telegram_username=message.from_user.username,
                telegram_fullname=message.from_user.full_name,
                name=data["name"],
                login=data["login"],
                created_at=datetime.now(timezone.utc)
            )

            print(f"Создается пользователь: {new_user}")
            db.add(new_user)

            await set_redis_cached_login(user_id=message.chat.id, login=data["login"])

            await db.commit()

            next_to_profile_form_kb_bd = InlineKeyboardBuilder()
            next_to_profile_form_kb_bd.button(
                text=LEXICON_RU['yes'], callback_data="to_filling_profile_form"
            )
            next_to_profile_form_kb_bd.button(
                text=LEXICON_RU['no'], callback_data="to_menu"
            )

            await message.answer(
                "Анкета заполнена!\nИмя: "
                f"<b>{data['name']}</b>\nЛогин: <b>{data['login']}</b>\n\n"
                "Если хотите изменить данные, отправьте команду /start, чтобы заполнить анкету заново.",
                parse_mode='HTML'
            )
            await message.answer(
                LEXICON_RU['offer_to_create_profile'],
                reply_markup=next_to_profile_form_kb_bd.as_markup()
            )
            print("Пользователь успешно создан.")
        except Exception as e:
            print(f"Ошибка создания пользователя: {e}")
            await db.rollback()
    else:
        await message.answer(LEXICON_RU['incorrect_login'], reply_markup=get_cancel_kb())
        return

    await state.clear()
