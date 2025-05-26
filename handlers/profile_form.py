from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from handlers_logic.states_factories import ProfileForm
from database.redis_query import set_redis_cached_profiles_list
from database.models import Profile
from database.orm_query import orm_get_user_own_profiles_list, orm_get_user
from lexicon.lexicon import LEXICON_RU
from keyboards.menu_kb import get_cancel_kb
from keyboards.profile_form_kb import (
    get_ask_for_have_diagnosis_kb, get_sex_kb,
    get_submit_profile_settings_kb, get_qeustion_about_species
)
from services.validators import (
    validate_name_of_profile_form, validate_age_of_profile_form,
    validate_less_than_40, validate_less_than_30
)
from services.redis_cache_data import get_cached_login

profile_form_router = Router()

@profile_form_router.callback_query(F.data == "to_filling_profile_form")
async def start_filling_profile_form(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    if await get_cached_login(db, callback.message.chat.id) == None:
        await state.clear()
        await callback.message.answer("Необходимо зарегистрироваться, чтобы создать профиль.\nНажмите на кнопку 'Меню' слева от строки ввода и выберите команду - /start")
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
        await message.answer("Вы создаете профиль для человека?", reply_markup=get_qeustion_about_species())
        await state.set_state(ProfileForm.biological_species)
    else:
        await message.answer(LEXICON_RU['incorrect_profile_name'])

@profile_form_router.callback_query(F.data == "profile_for_human", StateFilter(ProfileForm.biological_species))
async def process_about_species(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("У вас есть подтвержденный диагноз?", reply_markup=get_ask_for_have_diagnosis_kb())
    await state.set_state(ProfileForm.type_of_epilepsy)
    await callback.answer()

@profile_form_router.callback_query(F.data == "profile_for_animal", StateFilter(ProfileForm.biological_species))
async def process_about_species(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Для какого животного вы создаете профиль?", reply_markup=get_cancel_kb())
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.biological_species))
async def process_profile_for_animal(message: Message, state: FSMContext):
    if validate_less_than_30(message.text):
        await state.update_data(animal_species=message.text)
        await message.answer("У вас есть подтвержденный диагноз?", reply_markup=get_ask_for_have_diagnosis_kb())
        await state.set_state(ProfileForm.type_of_epilepsy)
    else:
        await message.answer("Вид животного не может быть длиннее 30 симовлов.", reply_markup=get_cancel_kb())


@profile_form_router.callback_query(F.data == "have_epilepsy_diagnosis",
                                    StateFilter(ProfileForm.type_of_epilepsy))
async def process_users_diagnosis(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите точную формулировку диагноза:",
                                reply_markup=get_cancel_kb())
    await callback.answer()

@profile_form_router.callback_query(F.data == "dont_have_epilepsy_diagnosis",
                                    StateFilter(ProfileForm.type_of_epilepsy))
async def process_skip_user_diagnosis(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(LEXICON_RU['enter_age'],
                                reply_markup=get_cancel_kb())
    await state.set_state(ProfileForm.age)
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.type_of_epilepsy))
async def process_diagnosis(message: Message, state: FSMContext):
    if validate_less_than_40(message.text):
        await state.update_data(type_of_epilepsy=message.text)
        await message.answer(LEXICON_RU['enter_age'],
                                reply_markup=get_cancel_kb())
        await state.set_state(ProfileForm.age)
    else:
        await message.answer("Длина диагноза не может быть больше 40 симолов")

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
    data = await state.get_data()
    profile_info = get_profile_info(data)
    await callback.message.answer(f"Анкета профиля заполнена!")
    await callback.message.answer(f"{profile_info}", parse_mode='HTML')
    await callback.message.answer("Нажмите 'Подтвердить', чтобы сохранить введенные данные или 'Отменить', чтобы ввести данные снова.",  reply_markup=get_submit_profile_settings_kb())
    await state.set_state(ProfileForm.check_form)
    await callback.answer()

@profile_form_router.callback_query(F.data == "submit_profile_settings", StateFilter(ProfileForm.check_form))
async def finish_filling_profile_data(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    print(f"Полученные данные: {data}")
    if not data:
        await callback.message.answer("Начните регистрацию заново")
        await state.clear()
        await callback.answer()
        return
    try:
        user = await orm_get_user(db, callback.message.chat.id)

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
            biological_species = data.get("animal_species", "Человек"),
            created_at=datetime.now(timezone.utc)
        )

        print(f"Создается профиль: {new_profile}")
        db.add(new_profile)

        profiles = await orm_get_user_own_profiles_list(db, callback.message.chat.id)

        await set_redis_cached_profiles_list(callback.message.chat.id, "user_own", profiles)

        await db.commit()
        print("Профиль успешно создан.")
    except Exception as e:
        print(f"Неизвестная ошибка при создании профиля: {e}")
        await db.rollback()

    await callback.message.answer(f"Профиль - {data['profile_name']} создан!")
    await state.clear()
    await callback.answer()

def get_profile_info(data: dict[str, str]) -> str:
    profile_info = (
        f'<u>Имя профиля</u>: <b>{data["profile_name"]}</b>\n'
        f'<u>Вид диагностированной эпилепсии</u>: <b>{"Неопределенного типа" if data.get("type_of_epilepsy", None) is None else data["type_of_epilepsy"]}</b>\n'
        f'<u>Возраст</u>: <b>{data["age"]} лет</b> \n'
        f'<u>Пол</u>: <b>{"Мужской" if data["sex"] == "male" else "Женский"}</b> \n'
        f'{'<u>Животное</u>: ' + data.get("animal_species", None) if data.get("animal_species", None) is not None else ''}'
    )
    return profile_info