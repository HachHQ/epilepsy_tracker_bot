import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import Command, StateFilter

from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder

from database.db_init import SessionLocal
from database.models import User, Profile, Drug, profile_drugs

from keyboards.menu_kb import get_cancel_kb
from keyboards.profile_form_kb import get_types_of_epilepsy_kb, get_sex_kb, get_timezone_kb, get_geolocation_for_timezone_kb, get_submit_profile_settings_kb

from services.validators import validate_name_of_profile_form, validate_age_of_profile_form, validate_list_of_drugs_of_profile_form

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
    if validate_name_of_profile_form(message.text):
        await state.update_data(profile_name=message.text)
        await message.answer("Выберите тип эпилепсии", reply_markup=get_types_of_epilepsy_kb())
        await state.set_state(ProfileForm.type_of_epilepsy)
    else:
        await message.answer("Имя может содержать только загланые и прописные буквы русского и английского алфавитов и быть от 1 до 40 символов в длину")

@profile_form_router.callback_query(F.data.in_({'focal_type', 'generalized_type',
                                    'combied_type','unidentified_type'}),
                                    StateFilter(ProfileForm.type_of_epilepsy))
async def process_type_of_epilepsy(callback: CallbackQuery, state: FSMContext):
    str_epilepsy_type = ""

    if callback.data == "focal_type":
        str_epilepsy_type = "Фокальная"
    elif callback.data == "generalized_type":
        str_epilepsy_type = "Генерализованная"
    elif callback.data == "combied_type":
        str_epilepsy_type = "Комбинированная"
    elif callback.data == "unidentified_type":
        str_epilepsy_type = "Неопределенного типа"

    await state.update_data(type_of_epilepsy=str_epilepsy_type)

    await callback.message.answer("Тут вы можете перечислить все лекастра, которые принмает\n"
                                    "тот для кого составляется анкета. Напишите их названия через запятую.\n"
                                    "Например: паглюферал, леветирацетам, пексион")
    await callback.message.answer("Введите принимаемые препараты:", reply_markup=get_cancel_kb())
    await state.set_state(ProfileForm.drugs)
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.drugs))
async def process_drugs(message: Message, state: FSMContext):
    if validate_list_of_drugs_of_profile_form(message.text):
        str_of_drugs = str(message.text)
        await state.update_data(drugs=str_of_drugs)
        await message.answer("Введите возраст:", reply_markup=get_cancel_kb())
        await state.set_state(ProfileForm.age)
    else:
        await message.answer("Список может содержать только буквы русского и английского алфавитов, цифры от 0 до 9 и символы , . и пробел")


@profile_form_router.message(StateFilter(ProfileForm.age))
async def process_age(message: Message, state: FSMContext):
    if validate_age_of_profile_form(message.text):
        await state.update_data(age=message.text)
        await message.answer("Выберите пол:", reply_markup=get_sex_kb())
        await state.set_state(ProfileForm.sex)
    else:
        await message.answer("Возраст может содержать только число от 1 до 130 включительно")


@profile_form_router.callback_query(F.data.in_({'sex_male', 'sex_female'}),
                                    StateFilter(ProfileForm.sex))
async def process_sex(callback: CallbackQuery, state: FSMContext):
    await state.update_data(sex=callback.data.split('_')[1])
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
    await callback.message.answer(f"Часовой пояс определен: {callback.data.split('_')[1]}",
                                    reply_markup=ReplyKeyboardRemove())
    await callback.message.answer(f"Анкета профиля заполнена!\nНажмите 'Подтвердить', чтобы проверить и сохранить введенные данные", reply_markup=get_submit_profile_settings_kb())
    await state.set_state(ProfileForm.check_form)
    await callback.answer()

@profile_form_router.callback_query(F.data == "submit_profile_settings")
async def finish_filling_profile_data(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    print(f"Полученные данные: {data}")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.message.chat.id).first()
        if not user:
            await callback.message.answer("Ошибка, пользователь не найден")
            return
        new_profile = Profile(
            user_id=user.id,
            profile_name=data["profile_name"],
            type_of_epilepsy=data["type_of_epilepsy"],
            age=data["age"],
            sex=data["sex"],
            timezone=data["timezone"],
            created_at=datetime.utcnow()
        )
        print(f"Создается профиль: {new_profile}")
        db.add(new_profile)
        db.flush()

        #user = db.query(User).filter(User.telegram_id == callback.message.chat.id).first()
        profile = db.query(Profile).filter((Profile.user_id == user.id) & (Profile.profile_name == data["profile_name"])).first()
        existing_drugs = {drug.name: drug.id for drug in db.query(Drug).all()}
        new_profile_drugs = []
        for drug_name in data["drugs"].strip().split(","):
            if drug_name in existing_drugs:
                drug_id = existing_drugs[drug_name]
            else:
                new_drug = Drug(name=drug_name)
                db.add(new_drug)
                db.flush()
                drug_id = new_drug.id
                existing_drugs[drug_name] = drug_id

            new_profile_drugs.append({"profile_id": profile.id, "drug_id": drug_id})
        db.execute(profile_drugs.insert(), new_profile_drugs)
        print("Препараты успешно добавлены к профилю.")

        db.commit()
        print("Профиль успешно создан.")
    except InterruptedError as e:
        print(f"Ошибка создания профиля: {e}")
        db.rollback()
    except Exception as e:
        print(f"Неизвестная ошибка при создании профиля: {e}")
    finally:
        db.close()

    # try:
    #     user = db.query(User).filter(User.telegram_id == callback.message.chat.id).first()
    #     profile = db.query(Profile).filter(Profile.user_id == user.id & Profile.profile_name == data["profile_name"]).first()
    #     existing_drugs = {drug.name: drug.id for drug in db.query(Drug).all()}
    #     new_profile_drugs = []
    #     for drug_name in data["drugs"].strip().split(","):
    #         if drug_name in existing_drugs:
    #             drug_id = existing_drugs[drug_name]
    #         else:
    #             new_drug = Drug(name=drug_name)
    #             db.add(new_drug)
    #             db.flush()
    #             drug_id = new_drug.id
    #             existing_drugs[drug_name] = drug_id

    #         new_profile_drugs.append({"profile_id": profile.id, "drug_id": drug_id})
    #     db.execute(profile_drugs.insert(), new_profile_drugs)
    #     print("Препараты успешно добавлены к профилю.")
    # except InterruptedError as e:
    #     print(f"Ошибка внесения лекарств: {e}")
    #     db.rollback()
    # except Exception as e:
    #     print(f"Неизвестная ошибка при внесеии лекарства: {e}")
    # finally:
    #     db.close()


    await callback.message.answer(f'Ваша анкета заполнена \nИмя профиля: {data["profile_name"]} \nТип эпилепсии: {data["type_of_epilepsy"]} \nПринимаемые препараты: {data["drugs"]} \nВозраст: {data["age"]} лет \nПол: {"Мужской" if data["sex"] == "male" else "Женский"} \nЧасовой пояс: {data["timezone"]}')
    await state.clear()
    await callback.answer()
