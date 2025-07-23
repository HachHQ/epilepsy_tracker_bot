import pytz
import hashlib
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from timezonefinder import TimezoneFinder

from handlers_logic.states_factories import UserForm
from database.models import User
from database.redis_query import set_redis_cached_login
from lexicon.lexicon import LEXICON_RU
from services.validators import validate_login_of_user_form, validate_name_of_user_form, validate_timezone, validate_codeword
from services.redis_cache_data import get_cached_login
from services.keyword_hasher import KeywordHasher
from keyboards.menu_kb import get_cancel_kb
from keyboards.profile_form_kb import get_timezone_kb, get_geolocation_for_timezone_kb

user_form_router = Router()

@user_form_router.callback_query(F.data == "submit_welcome_msg")
async def start_form(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    user_is_exist = await get_cached_login(db, callback.message.chat.id)
    if user_is_exist is not None:
        await state.clear()
        await callback.message.edit_text("Вы уже зарегистрированы")
        await callback.answer()
        return
    await callback.message.answer(LEXICON_RU['enter_username'], reply_markup=get_cancel_kb())
    await state.set_state(UserForm.name)
    await callback.answer()

@user_form_router.message(StateFilter(UserForm.name))
async def process_name(message: Message, state: FSMContext):
    if validate_name_of_user_form(message.text):
        print("Имя валидно")
        await state.update_data(name=message.text)
        await message.answer("Имя сохранено.", reply_markup=get_geolocation_for_timezone_kb())
        await message.answer(LEXICON_RU['timezone_info'], reply_markup=get_timezone_kb(), parse_mode='MarkDownV2')
        await state.set_state(UserForm.timezone)
    else:
        await message.answer("Имя должно иметь длину от 1 до 20 символов, и использовать только буквы русского или английского алфавита", reply_markup=get_cancel_kb())
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
        await state.update_data(timezone=f"{int(utc_offset_hours):+}")
        data = await state.get_data()
        await message.answer(f"Часовой пояс определен: {int(utc_offset_hours):+}", reply_markup=ReplyKeyboardRemove())
        await message.answer(
                (
                    f"Ввведите ключевое слово, с помощью которого, в дальшейшем мы сможем идентифицировать вас, "
                    f"в случае если вы потеряете доступ к телефону/телеграмму.\n\n"
                    f"Ключевое слово может быть любым, содержать любые буквы/цифры/знаки. Иметь длину от 8 до 25 символов.\n\n"
                    f"Запомните его или запишите!"
                ),
            reply_markup=get_cancel_kb()
            )
        await state.set_state(UserForm.codeword)
    else:
        await message.answer("Часовой пояс не найден, воспользуйтесь клавиатурой или вводом.")



@user_form_router.callback_query(F.data.contains("timezone_"),
                                    StateFilter(UserForm.timezone))
async def process_timezone(callback: CallbackQuery, state: FSMContext):
    await state.update_data(timezone=callback.data.split('_')[1])
    await callback.message.answer(f"Часовой пояс определен: {callback.data.split('_')[1]}",
                                    reply_markup=ReplyKeyboardRemove())
    await callback.message.answer(
            (
                f"Ввведите ключевое слово, с помощью которого, в дальшейшем мы сможем идентифицировать вас, "
                f"в случае если вы потеряете доступ к телефону/телеграмму.\n\n"
                f"Ключевое слово может быть любым, содержать любые буквы/цифры/знаки. Иметь длину от 8 до 25 символов.\n\n"
                f"Запомните его или запишите! После ввода сообщение удалится."
            ),
        reply_markup=get_cancel_kb()
        )
    await state.set_state(UserForm.code_word)
    await callback.answer()

@user_form_router.message(StateFilter(UserForm.timezone))
async def process_timezone_by_msg(message: Message, state: FSMContext):
    timezone = message.text
    if validate_timezone(timezone):
        await state.update_data(timezone=timezone)
        await message.answer(f"Часовой пояс определен: {timezone}", reply_markup=ReplyKeyboardRemove())
        await message.answer(
            (
                f"Ввведите ключевое слово, с помощью которого, в дальшейшем мы сможем идентифицировать вас, "
                f"в случае если вы потеряете доступ к телефону/телеграмму.\n\n"
                f"Ключевое слово может быть любым, содержать любые буквы/цифры/знаки. Иметь длину от 8 до 25 символов.\n\n"
                f"Запомните его или запишите! После ввода сообщение удалится."
            ),
        reply_markup=get_cancel_kb()
        )
        await state.set_state(UserForm.code_word)
    else:
        await message.answer("Часовой пояс должен иметь формат - +7 или +3", reply_markup=get_cancel_kb())

@user_form_router.message(StateFilter(UserForm.code_word))
async def process_codeword(message: Message, state: FSMContext):
    code_word = message.text
    if validate_codeword(code_word):
        hasher = KeywordHasher()
        hashed_codeword = hasher.hash_keyword(code_word)
        await state.update_data(codeword=hashed_codeword)
        print(hashed_codeword)
        await state.set_state(UserForm.login)
        await message.answer(LEXICON_RU['enter_login'], reply_markup=get_cancel_kb())

    else:
        await message.answer(f"Ключевое слово может быть любым, содержать любые буквы/цифры/знаки. Иметь длину от 8 до 25 символов.\n\nЗапомните его или запишите!", reply_markup=get_cancel_kb())

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
                timezone=data["timezone"],
                keyword_hash = data['codeword'],
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
