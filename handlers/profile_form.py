import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import Command, StateFilter
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timezone
import pytz
from timezonefinder import TimezoneFinder

from database.models import User, Profile, Drug, profile_drugs

from lexicon.lexicon import LEXICON_RU

from keyboards.menu_kb import get_cancel_kb
from keyboards.profile_form_kb import get_types_of_epilepsy_kb, get_sex_kb, get_timezone_kb, get_geolocation_for_timezone_kb, get_submit_profile_settings_kb

from services.validators import validate_name_of_profile_form, validate_age_of_profile_form, validate_list_of_drugs_of_profile_form
from services.redis_cache_data import get_cached_login, set_cached_profiles_list

profile_form_router = Router()

class ProfileForm(StatesGroup):
    profile_name = State()
    type_of_epilepsy = State()
    drugs = State()
    age = State()
    sex = State()
    timezone = State()
    check_form = State()

@profile_form_router.callback_query(F.data == "to_filling_profile_form")
async def start_filling_profile_form(callback: CallbackQuery, state: FSMContext):
    if await get_cached_login(callback.message.chat.id) == "Не зарегистрирован":
        await state.clear()
        await callback.message.answer("Необходимо зарегистрироваться, чтобы создать профиль.\nВыберите в меню слева от строки ввода меню и нажмите /start")
        await callback.answer()
        return
    await callback.message.answer(LEXICON_RU['info_about_profile'], parse_mode="HTML")
    await callback.message.answer(LEXICON_RU['enter_profile_name'], reply_markup=get_cancel_kb())
    await state.set_state(ProfileForm.profile_name)
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.profile_name))
async def process_profile_name(message: Message, state: FSMContext):
    if validate_name_of_profile_form(message.text):
        await state.update_data(profile_name=message.text)
        await message.answer(LEXICON_RU['enter_type_of_epilepsy'], reply_markup=get_types_of_epilepsy_kb())
        await state.set_state(ProfileForm.type_of_epilepsy)
    else:
        await message.answer(LEXICON_RU['incorrect_profile_name'])

@profile_form_router.callback_query(F.data.in_({'focal_type', 'generalized_type',
                                    'combied_type','unidentified_type'}),
                                    StateFilter(ProfileForm.type_of_epilepsy))
async def process_type_of_epilepsy(callback: CallbackQuery, state: FSMContext):
    await state.update_data(type_of_epilepsy=callback.data)
    await callback.message.answer(LEXICON_RU['enter_drugs_info'],
                                    parse_mode="HTML")
    await callback.message.answer(LEXICON_RU['enter_drugs'],
                                reply_markup=get_cancel_kb())
    await state.set_state(ProfileForm.drugs)
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.drugs))
async def process_drugs(message: Message, state: FSMContext):
    if validate_list_of_drugs_of_profile_form(message.text) and len(message.text) <= 120:
        str_of_drugs = str(message.text)
        await state.update_data(drugs=str_of_drugs)
        await message.answer(LEXICON_RU['incorrect_age'],
                            parse_mode="HTML")
        await message.answer(LEXICON_RU['enter_age'],
                            reply_markup=get_cancel_kb())
        await state.set_state(ProfileForm.age)
    else:
        await message.answer(LEXICON_RU['incorrect_drugs'],
                            parse_mode='HTML')

@profile_form_router.message(StateFilter(ProfileForm.age))
async def process_age(message: Message, state: FSMContext):
    if validate_age_of_profile_form(message.text):
        await state.update_data(age=message.text)
        await message.answer(LEXICON_RU['enter_sex'], reply_markup=get_sex_kb())
        await state.set_state(ProfileForm.sex)
    else:
        await message.answer(LEXICON_RU['incorrect_age'], parse_mode='HTML')

@profile_form_router.callback_query(F.data.in_({'sex_male', 'sex_female'}),
                                    StateFilter(ProfileForm.sex))
async def process_sex(callback: CallbackQuery, state: FSMContext):
    await state.update_data(sex=callback.data.split('_')[1])
    await callback.message.answer(LEXICON_RU['timezone_info'],reply_markup=get_geolocation_for_timezone_kb())
    await callback.message.answer("Выберите ваш часовой пояс или нажмите на кнопку снизу:", reply_markup=get_timezone_kb())
    await state.set_state(ProfileForm.timezone)
    await callback.answer()

@profile_form_router.message(F.location, StateFilter(ProfileForm.timezone))
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
        profile_info = get_profile_info(data)
        await message.answer(f"Часовой пояс определен: {int(utc_offset_hours):+}", reply_markup=ReplyKeyboardRemove())
        await message.answer(f"Анкета профиля заполнена!")
        await message.answer(f"{profile_info}", parse_mode='HTML')
        await message.answer("Нажмите 'Подтвердить', чтобы сохранить введенные данные или 'Отменить', чтобы ввести данные снова.",  reply_markup=get_submit_profile_settings_kb())
        await state.set_state(ProfileForm.check_form)
    else:
        await message.answer("Часовой пояс не найден, воспользуйтесь клавиатурой")



@profile_form_router.callback_query(F.data.contains("timezone_"),
                                    StateFilter(ProfileForm.timezone))
async def process_timezone(callback: CallbackQuery, state: FSMContext):
    await state.update_data(timezone=callback.data.split('_')[1])
    data = await state.get_data()
    profile_info = get_profile_info(data)
    await callback.message.answer(f"Часовой пояс определен: {callback.data.split('_')[1]}",
                                    reply_markup=ReplyKeyboardRemove())
    await callback.message.answer(f"Анкета профиля заполнена!")
    await callback.message.answer(f"{profile_info}", parse_mode="HTML")
    await callback.message.answer("Нажмите 'Подтвердить', чтобы сохранить введенные данные или 'Отменить', чтобы ввести данные снова.",  reply_markup=get_submit_profile_settings_kb())
    await state.set_state(ProfileForm.check_form)
    await callback.answer()


@profile_form_router.callback_query(F.data == "submit_profile_settings")
async def finish_filling_profile_data(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    print(f"Полученные данные: {data}")
    if not data:
        await callback.message.answer("Начните регистрацию заново")
        await state.clear()
        await callback.answer()
        return
    try:
        result = await db.execute(select(User).filter(User.telegram_id == callback.message.chat.id))
        user = result.scalars().first()

        if not user:
            await callback.message.answer("Ошибка, пользователь не найден")
            await state.clear()
            return
        new_profile = Profile(
            user_id=user.id,
            profile_name=data["profile_name"],
            type_of_epilepsy=data["type_of_epilepsy"],
            age=int(data["age"]),
            sex=data["sex"],
            timezone=data["timezone"],
            created_at=datetime.now(timezone.utc)
        )

        print(f"Создается профиль: {new_profile}")
        db.add(new_profile)
        await db.flush()
        profile_id = new_profile.id
        result = await db.execute(select(Profile).filter(Profile.id == profile_id))
        profile = result.scalars().first()

        existing_drugs = {drug.name: drug.id for drug in (await db.execute(select(Drug))).scalars()}
        new_profile_drugs = []

        for drug_name in data["drugs"].lower().strip().split(","):
            if drug_name in existing_drugs:
                drug_id = existing_drugs[drug_name.strip()]
            else:
                new_drug = Drug(name=drug_name.strip())
                db.add(new_drug)
                await db.flush()
                drug_id = new_drug.id
                existing_drugs[drug_name.strip()] = drug_id

            new_profile_drugs.append({"profile_id": profile.id, "drug_id": drug_id})

        await db.execute(profile_drugs.insert().values(new_profile_drugs))
        print("Препараты успешно добавлены к профилю.")
        query = (
                select(Profile)
                .join(User)
                .where(User.telegram_id == callback.message.chat.id)
            )
        profiles_result = await db.execute(query)
        profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
        
        await set_cached_profiles_list(callback.message.chat.id, "user_own", profiles)

        await db.commit()
        print("Профиль успешно создан.")
    except Exception as e:
        print(f"Неизвестная ошибка при создании профиля: {e}")
        await db.rollback()

    await callback.message.answer(f"Профиль - {data['profile_name']} создан!")
    await state.clear()
    await callback.answer()

def get_profile_info(data: dict[str, str]) -> str:
    str_epilepsy_type = ""

    if data['type_of_epilepsy'] == "focal_type":
        str_epilepsy_type = "Фокальная"
    elif data['type_of_epilepsy'] == "generalized_type":
        str_epilepsy_type = "Генерализованная"
    elif data['type_of_epilepsy'] == "combied_type":
        str_epilepsy_type = "Комбинированная"
    elif data['type_of_epilepsy'] == "unidentified_type":
        str_epilepsy_type = "Неопределенного типа"
    profile_info = f'<u>Имя профиля</u> : <b>{data["profile_name"]}</b>\n<u>Тип эпилепсии</u> : <b>{str_epilepsy_type}</b>\n<u>Принимаемые препараты</u> : <b>{data["drugs"]}</b>\n<u>Возраст</u> : <b>{data["age"]} лет</b> \n<u>Пол</u> : <b>{"Мужской" if data["sex"] == "male" else "Женский"}</b> \n<u>Часовой пояс</u> : <b>{data["timezone"]}</b>'

    return profile_info