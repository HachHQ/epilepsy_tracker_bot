from mailbox import Message
import profile
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import StateFilter
from datetime import datetime

from database.orm_query import (
    orm_create_medication_course, orm_get_profile_medication_by_id, orm_delete_profile_medication,
    orm_update_medication_attribute, orm_get_profile_medications_list
)
from handlers_logic.states_factories import MedicationCourse
from keyboards.profiles_list_kb import get_profile_submenu_kb
from keyboards.medication_kb import get_medication_sumbenu
from keyboards.menu_kb import get_cancel_kb
from keyboards.journal_kb import get_nav_btns_for_list
from keyboards.medication_kb import get_skip_cancel_buttons, get_actual_med_cancel_buttons, get_deleting_medication_kb
from services.redis_cache_data import get_cached_current_profile
from services.validators import validate_less_than_40, validate_less_than_60, validate_date

medication_router = Router()

from config_data.pagination import MEDICATIONS_PER_PAGE as NOTES_PER_PAGE

@medication_router.callback_query(F.data == 'medication')
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите действие: \n- Добавить курс препарата\n- Изменить существующий курс (Управление)",
        reply_markup=get_medication_sumbenu()
    )
    await callback.answer()

@medication_router.callback_query(F.data == "add_medication")
async def process_add_medication(callback: CallbackQuery, state: FSMContext):
    validator_error = "Длина названия препарата не может быть больше 40 символов."
    text = (
        "Напишите название препарата. Это может как торговое так и рыночное наименование, как вам удобно.\n\n"
        "Длина названия препарата не может быть выше 40 символов."
    )
    await state.set_state(MedicationCourse.medication_name)
    await callback.message.answer(text, reply_markup=get_cancel_kb())

@medication_router.message(StateFilter(MedicationCourse.medication_name))
async def process_medication_name(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    validator_error = "Длина названия препарата не может быть больше 40 символов."
    if validate_less_than_40(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'medication_name', message.text)
            await message.answer(f"Название лекарства обновлено: {message.text}")
            await state.clear()
            return
        await state.update_data(medication_name=message.text)
        val = "Длина дозировки препарата не может быть больше 40 символов."
        text = (
            "Введите принимаемую дозировку (Например: 150мг или 50г):\n\n"
            f"{val}"
        )
        await state.set_state(MedicationCourse.dosage)
        await message.answer(text, reply_markup=get_cancel_kb())
    else:
        await message.answer(validator_error, reply_markup=get_cancel_kb())

@medication_router.message(StateFilter(MedicationCourse.dosage))
async def process_medication_dosage(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    validator_error = "Длина дозировки препарата не может быть больше 40 символов."
    if validate_less_than_40(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'dosage', message.text)
            await message.answer(f"Дозировка лекарства обновлена: {message.text}")
            await state.clear()
            return
        await state.update_data(dosage=message.text)
        val = "Длина строки описывающей частоту приема препарата не может быть больше 60 символов."
        text = (
            "Введите частоту приема лекарства дозировку (Например: 2 раза в день или раз в день):\n\n"
            f"{val}"
        )
        await state.set_state(MedicationCourse.frequency)
        await message.answer(text, reply_markup=get_cancel_kb())
    else:
        await message.answer(validator_error, reply_markup=get_cancel_kb())

@medication_router.message(StateFilter(MedicationCourse.frequency))
async def process_medication_frequency(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    validator_error = "Длина строки описывающей частоту приема препарата не может быть больше 60 символов."
    if validate_less_than_40(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'frequency', message.text)
            await message.answer(f"Частота приема для курса лекарства обновлена: {message.text}")
            await state.clear()
            return
        await state.update_data(frequency=message.text)
        val = "Длина строки описывающей заметку к приему препарата не может быть больше 60 символов."
        text = (
            "Введите заметку о лекарстве, в вольном формате (Может врач дал вам какие-то рекомендации к приему, которые стоит зафиксировать):\n"
            "Вы можете пропустить этот шаг нажав на '⏩ Пропустить шаг'.\n\n"
            f"{val}"
        )
        await state.set_state(MedicationCourse.notes)
        await message.answer(text, reply_markup=get_skip_cancel_buttons())
    else:
        await message.answer(validator_error, reply_markup=get_cancel_kb())

@medication_router.callback_query(F.data == 'skip_note_for_medication', StateFilter(MedicationCourse.notes))
async def process_medication_notes(callback: CallbackQuery, state: FSMContext):
    text = (
            "Введите дату начала приема лекарства в формате - 2000-02-30 (год, день, месяц). Это нужно для отслеживания его эффективности:\n\n"
        )
    await state.set_state(MedicationCourse.start_date)
    await callback.message.answer(text, reply_markup=get_cancel_kb())
    await callback.answer()

@medication_router.message(StateFilter(MedicationCourse.notes))
async def process_medication_notes(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    validator_error = "Длина строки описывающей заметку к приему препарата не может быть больше 60 символов."
    if validate_less_than_60(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'notes', message.text)
            await message.answer(f"Заметка для курса лекарства обновлена: {message.text}")
            await state.clear()
            return
        await state.update_data(notes=message.text)
        text = (
            "Введите дату начала приема лекарства в формате - 2000-02-30 (год, день, месяц). Это нужно для отслеживания его эффективности:\n\n"
        )
        await state.set_state(MedicationCourse.start_date)
        await message.answer(text, reply_markup=get_cancel_kb())
    else:
        await message.answer(validator_error, reply_markup=get_cancel_kb())

@medication_router.message(StateFilter(MedicationCourse.start_date))
async def process_medication_start_date(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    validator_error = "Дата должна быть в формате - 2000-02-30 (год, день, месяц)"
    if validate_date(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            prof_start_date_dt = datetime.strptime(message.text, "%Y-%m-%d")
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'start_date', prof_start_date_dt)
            await message.answer(f"Дата начала курса лекарства обновлена: {message.text}")
            await state.clear()
            return
        await state.update_data(start_date=message.text)
        text = (
            "Если вы все еще принимаете препарат, для которого заполняете анкету, то нажмите на - '⌛ Еще принимаю'\n\n"
            "Если же вы вводите данные о препарате курс которого окончен, то введите дату в таком же формате как и в предыдущем шаге.\n"
            "Сохранение в системе препаратов курс приема которых окончен также помогает наглядно учесть его эффективность, если в системе есть данные о приступах, зафиксированных во время его приема. \n\n"
            f"{validator_error}"
        )
        await state.set_state(MedicationCourse.end_date)
        await message.answer(text, reply_markup=get_actual_med_cancel_buttons())
    else:
        await message.answer(validator_error, reply_markup=get_cancel_kb())

@medication_router.callback_query(F.data == 'skip_end_date_for_medication', StateFilter(MedicationCourse.end_date))
async def process_medication_confirm(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    medication_name = data.get("medication_name", None)
    dosage = data.get("dosage", None)
    frequency = data.get('frequency', None)
    notes = data.get("notes", None)
    start_date = data.get("start_date", None)
    end_date = data.get("end_date", None)
    profile_id = await get_cached_current_profile(db, callback.message.chat.id)
    print(profile_id)
    medication_list = [int(profile_id.split('|')[0]), medication_name, dosage, frequency, notes, start_date, end_date]
    await orm_create_medication_course(db, *medication_list)
    text = (
                "Курс лекарства добавлен\n\n"
                f"Название лекарства: {medication_name if medication_name else "Не введено"}\n"
                f"Дозировка: {dosage if dosage else "Не введено"}\n"
                f"Частота приема: {frequency if frequency else "Не введено"}\n"
                f"Заметка: {notes if notes else "Не введено"}\n"
                f"Начало приема курса: {start_date if start_date else "Не введено"}\n"
                f"Конец приема курса: {end_date if end_date else "Не введено"}\n"
            )
    await state.clear()
    await callback.message.answer(text)
    await callback.answer()

@medication_router.message(StateFilter(MedicationCourse.end_date))
async def process_medication_end_date(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    validator_error = "Дата должна быть в формате - 2000-02-30 (год, день, месяц)"
    if validate_date(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            prof_end_date_dt = datetime.strptime(message.text, "%Y-%m-%d")
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'end_date', prof_end_date_dt)
            await message.answer(f"Дата окончания курса лекарства обновлена: {message.text}")
            await state.clear()
            return
        await state.update_data(end_date=message.text)
        data = await state.get_data()
        medication_name = data.get("medication_name", None)
        dosage = data.get("dosage", None)
        frequency = data.get('frequency', None)
        notes = data.get("notes", None)
        start_date = data.get("start_date", None)
        end_date = data.get("end_date", None)
        profile_id = await get_cached_current_profile(db, message.chat.id)
        print(profile_id)
        medication_list = [int(profile_id.split('|')[0]), medication_name, dosage, frequency, notes, start_date, end_date]
        await orm_create_medication_course(db, *medication_list)
        text = (
                "Курс лекарства добавлен\n\n"
                f"Название лекарства: {medication_name if medication_name else "Не введено"}\n"
                f"Дозировка: {dosage if dosage else "Не введено"}\n"
                f"Частота приема: {frequency if frequency else "Не введено"}\n"
                f"Заметка: {notes if notes else "Не введено"}\n"
                f"Начало приема курса: {start_date if start_date else "Не введено"}\n"
                f"Конец приема курса: {end_date if end_date else "Не введено"}\n"
            )
        await state.clear()
        await message.answer(text)
    else:
        await message.answer(validator_error, reply_markup=get_cancel_kb())

def display_medications(profile_medications, current_page):
    current_page = int(current_page)
    start_index = current_page * NOTES_PER_PAGE
    end_index = int(start_index) + NOTES_PER_PAGE
    profile_md_on_page = profile_medications[start_index:end_index]
    text = ""
    for profile_mdc in profile_md_on_page:
        line = (
            f"💊 - {profile_mdc.medication_name} {profile_mdc.dosage} - /mdcedit_{profile_mdc.id}\n\n"
        )
        text += line
    return text

@medication_router.callback_query(F.data == 'medication_settings')
async def process_medication_display(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    profile_id = await get_cached_current_profile(db, callback.message.chat.id)
    profile_medications = await orm_get_profile_medications_list(db, int(profile_id.split('|')[0]))
    if profile_medications is None:
        await callback.message.answer("У вас нет добавленных курсов лекарств.")
    text = f"Ваши курсы лекарств (Всего {len(profile_medications)})\n\n"
    text += display_medications(profile_medications, 0)
    await callback.message.answer(text, parse_mode='HTML', reply_markup=get_nav_btns_for_list(len(profile_medications), NOTES_PER_PAGE, 0, 'profile_medications_journal'))
    await callback.answer()

@medication_router.callback_query(F.data.startswith('profile_medications_journal'))
async def process_medication_list_pagination(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, page = callback.data.split(':', 1)
    profile_id = await get_cached_current_profile(db, callback.message.chat.id)
    profile_medications = await orm_get_profile_medications_list(db, int(profile_id.split('|')[0]))
    if profile_medications is None:
        await callback.message.answer("У вас нет добавленных курсов лекарств.")
    text = f"Ваши курсы лекарств (Всего {len(profile_medications)})\n\n"
    text += display_medications(profile_medications, page)
    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_nav_btns_for_list(len(profile_medications), NOTES_PER_PAGE, page, 'profile_medications_journal'))
    await callback.answer()

@medication_router.message(F.text.startswith('/mdcedit'))
async def process_pagination_of_medicine_list(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    mdc_id = message.text.split('_', 1)[1]
    profile_id = await get_cached_current_profile(db, message.chat.id)
    profile_mdc = await orm_get_profile_medication_by_id(db, int(profile_id.split('|')[0]), int(mdc_id))
    if profile_mdc is None:
        await message.answer('Нет такой записи.')
        return
    text = (
        f"Настройки курса для профиля - {profile_id.split('|')[1]}\n\n"
        f"💊 Название лекарства: {profile_mdc.medication_name} - /mdc_medname_{profile_mdc.id}\n"
        f"⏲️ Дозировка: {profile_mdc.dosage} - /mdc_dos_{profile_mdc.id}\n"
        f"🔰 Частота приема: {profile_mdc.frequency} - /mdc_freq_{profile_mdc.id}\n"
        f"🗒️ Заметка: {"Не заполнено" if profile_mdc.notes is None else profile_mdc.notes} - /mdc_note_{profile_mdc.id}\n"
        f"⏱️ Начало приема курса: {profile_mdc.start_date} - /mdc_strdt_{profile_mdc.id}\n"
        f"⏱️ Конец приема курса: {"Не введено" if profile_mdc.end_date is None else profile_mdc.end_date} - /mdc_enddt_{profile_mdc.id}\n"
        f"🗑️ Удалить запись о курсе: - /mdc_del_{profile_mdc.id}"
    )
    await message.answer(text)

@medication_router.message(F.text.startswith('/mdc'))
async def process_editing_medication_settings(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, action, mdc_id = message.text.split('_', 2)
    profile_id = await get_cached_current_profile(db, message.chat.id)
    profile_mdc = await orm_get_profile_medication_by_id(db, int(profile_id.split('|')[0]), int(mdc_id))
    if profile_mdc is None:
        await message.answer('Нет такой записи.')
        return
    await state.update_data(mdcmode="mdc_prof_edit", profile_id=profile_id.split('|')[0], mdc_id=mdc_id)
    if action == "medname":
        validator_error = "Длина названия препарата не может быть больше 40 символов."
        text = (
            "Напишите название препарата. Это может как торговое так и рыночное наименование, как вам удобно.\n\n"
            f"{validator_error}"
        )
        await message.answer(text)
        await state.set_state(MedicationCourse.medication_name)
    elif action == "dos":
        val = "Длина дозировки препарата не может быть больше 40 символов."
        text = (
            "Введите принимаемую дозировку (Например: 150мг или 50г):\n\n"
            f"{val}"
        )
        await message.answer(text)
        await state.set_state(MedicationCourse.dosage)
    elif action == "freq":
        val = "Длина строки описывающей частоту приема препарата не может быть больше 60 символов."
        text = (
            "Введите частоту приема лекарства дозировку (Например: 2 раза в день или раз в день):\n\n"
            f"{val}"
        )
        await message.answer(text)
        await state.set_state(MedicationCourse.frequency)
    elif action == "note":
        val = "Длина строки описывающей заметку к приему препарата не может быть больше 60 символов."
        text = (
            "Введите заметку о лекарстве, в вольном формате:\n"
            f"{val}"
        )
        await message.answer(text)
        await state.set_state(MedicationCourse.notes)
    elif action == 'strdt':
        text = (
            "Введите дату начала приема лекарства в формате - 2000-02-30 (год, день, месяц). Это нужно для отслеживания его эффективности:\n\n"
        )
        await message.answer(text)
        await state.set_state(MedicationCourse.start_date)
    elif action == 'enddt':
        text = (
            "Введите дату окончания приема лекарства в формате - 2000-02-30 (год, день, месяц). Это нужно для отслеживания его эффективности:\n\n"
        )
        await message.answer(text)
        await state.set_state(MedicationCourse.end_date)
    elif action == 'del':
        text = (
            "Вы действительно хотите удалить этот курс лекарства?"
        )
        await message.answer(text, reply_markup=get_deleting_medication_kb(mdc_id, int(profile_id.split('|')[0])))
    else:
        await message.answer("Нет такой команды.")

@medication_router.callback_query(F.data.startswith("delete_med_prof"))
async def process_confirm_deleting_notify(callback: CallbackQuery, db: AsyncSession):
    _, answer, mdc_id, prof_id = callback.data.split(':', 3)
    if answer == 'yes':
        print('yes')
        res = await orm_delete_profile_medication(db, int(prof_id), int(mdc_id))
        print('res')
        if res:
            await callback.message.answer("Курс лекарства успешно удален.")
        else:
            await callback.message.answer("Нет такой записи.")
    else:
        await callback.message.answer("Удаление курса лекарства отменено.")
    await callback.answer()
