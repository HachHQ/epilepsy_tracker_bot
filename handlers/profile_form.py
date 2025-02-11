import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import Command, StateFilter

from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder

from keyboards.menu_kb import get_cancel_kb
from keyboards.profile_form_kb import get_types_of_epilepsy_kb, get_sex_kb, get_timezone_kb, get_geolocation_for_timezone_kb, get_submit_profile_settings_kb

profile_form_router = Router()

class ProfileForm(StatesGroup):
    profile_name = State()
    type_of_epilepsy = State()
    drugs = State()
    age = State()
    sex = State()
    timezone = State()
    check_form = State()

#TODO   write validator for each input field
#TODO   write sql-query to save profile data and associate it with user profile

@profile_form_router.message(Command(commands="cancel"), ~StateFilter(default_state))
async def cancel_form(message: Message, state: FSMContext):
    await message.answer(
        "Вы отменили заполнение анкеты.\n"
        "Чтобы начать заново, отправьте команду /start.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

@profile_form_router.message(Command(commands="cancel"), StateFilter(default_state))
async def cancel_outside_fsm(message: Message):
    await message.answer(
        "Вы не находитесь в процессе заполнения анкеты.\n"
        "Чтобы начать заполнение, используйте команду /start.",
        reply_markup=ReplyKeyboardRemove()
    )

#TODO Завершить удаление клавиатуры отправки геолокации
@profile_form_router.callback_query(F.data == "cancel_fsm_script", ~StateFilter(default_state))
async def cancel_fsm_script(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Вы отменили заполнение анкеты, чтобы начать заново, отправьте команду /start",
                                    reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await callback.answer()

@profile_form_router.callback_query(F.data == "to_filling_profile_form")
async def start_filling_profile_form(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Вы можете создать профиль для себя, родственника, "
                                    "или своего питомца. Заполните анкету его специфичными данными, именем (или кличкой),"
                                    "видом эпилепсии, принимаемыми препаратами и так далее.")
    await callback.message.answer("Введите имя профиля", reply_markup=get_cancel_kb())
    await state.set_state(ProfileForm.profile_name)
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.profile_name))
async def process_profile_name(message: Message, state: FSMContext):
    await state.update_data(profile_name=message.text)

    await message.answer("Выберите тип эпилепсии", reply_markup=get_types_of_epilepsy_kb())
    await state.set_state(ProfileForm.type_of_epilepsy)

@profile_form_router.callback_query(F.data.in_({'focal_type', 'generalized_type',
                                    'combied_type','unidentified_type'}),
                                    StateFilter(ProfileForm.type_of_epilepsy))
async def process_type_of_epilepsy(callback: CallbackQuery, state: FSMContext):
    await state.update_data(type_of_epilepsy=callback.data)
    await callback.message.answer("Тут вы можете перечислить все лекастра, которые принмает\n"
                                    "тот для кого составляется анкета. Напишите их названия через запятую.\n"
                                    "Например: паглюферал, леветирацетам, пексион")
    await callback.message.answer("Введите принимаемые препараты:")
    await state.set_state(ProfileForm.drugs)
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.drugs))
async def process_drugs(message: Message, state: FSMContext):
    #TODO validator
    str_of_drugs = str(message.text)
    await state.update_data(drugs=str_of_drugs)
    await message.answer("Введите возраст:")
    await state.set_state(ProfileForm.age)

@profile_form_router.message(StateFilter(ProfileForm.age))
async def process_age(message: Message, state: FSMContext):
    #TODO validator
    await state.update_data(age=message.text)
    await message.answer("Выберите пол:", reply_markup=get_sex_kb())
    await state.set_state(ProfileForm.sex)

@profile_form_router.callback_query(F.data.in_({'sex_male', 'sex_female'}),
                                    StateFilter(ProfileForm.sex))
async def process_sex(callback: CallbackQuery, state: FSMContext):
    await state.update_data(sex=callback.data)
    await callback.message.answer("Зная ваш часовой пояс бот сможет вовремя присылать вам уведомления о приеме лекарств. \n"
                            "Введите его в UTC формате, например: +7 (для Новосибирска) или +3 (для Москвы)\n"
                            "По этой ссылке можно узнать часовой пояс в UTC формате вашего города:\n"
                            "https://time-in.ru/time/russia \n"
                            "Вы так же можете воспользоваться автоматическим определением часового пояса, нажав на кнопку под строкой ввода, внизу.\n"
                            "Бот не хранит важе местоположение, только часовой пояс."
                            ,reply_markup=get_geolocation_for_timezone_kb())
    await callback.message.answer("Выберите ваш часовой пояс или нажмите на кнопку снизу и бот сам определит ваш часовой пояс:", reply_markup=get_timezone_kb())
    # await state.set_state(ProfileForm.check_form)
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
        await message.answer(f"Часовой пояс определен: {int(utc_offset_hours):+}", reply_markup=ReplyKeyboardRemove())
        await message.answer(f"Анкета профиля заполнена!\nНажмите 'Подтвердить', чтобы проверить и сохранить введенные данные", reply_markup=get_submit_profile_settings_kb())
        await state.update_data(timezone=f"{int(utc_offset_hours):+}")
        await state.set_state(ProfileForm.check_form)
    else:
        await message.answer("Часовой пояс не найден, воспользуйтесь клавиатурой")



@profile_form_router.callback_query(F.data.contains("timezone_"),
                                    StateFilter(ProfileForm.timezone))
async def process_timezone(callback: CallbackQuery, state: FSMContext):
    await state.update_data(timezone=callback.data.split('_')[1])
    # data = await state.get_data()
    await callback.message.answer(f"Часовой пояс определен: {callback.data.split('_')[1]}",
                                    reply_markup=ReplyKeyboardRemove())
    await callback.message.answer(f"Анкета профиля заполнена!\nНажмите 'Подтвердить', чтобы проверить и сохранить введенные данные", reply_markup=get_submit_profile_settings_kb())
    await state.set_state(ProfileForm.check_form)
    await callback.answer()

@profile_form_router.callback_query(F.data == "submit_profile_settings")
async def finish_filling_profile_data(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.answer(f'Ваша анкета заполнена \nИмя профиля: {data["profile_name"]} \nТип эпилепсии: {data["type_of_epilepsy"]} \nПринимаемые препараты: {data["drugs"]} \nВозраст: {data["age"]} лет \nПол: {"Мужской" if data["sex"] == "sex_male" else "Женский"} \nЧасовой пояс: {data["timezone"]}')
    await state.clear()
    await callback.answer()