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
from i18n import t
from keyboards.profiles_list_kb import get_profile_submenu_kb
from keyboards.medication_kb import get_medication_sumbenu
from keyboards.menu_kb import get_cancel_kb
from keyboards.journal_kb import get_nav_btns_for_list
from keyboards.medication_kb import get_skip_cancel_buttons, get_actual_med_cancel_buttons, get_deleting_medication_kb
from services.redis_cache_data import get_cached_current_profile
from services.validators import validate_less_than_40, validate_less_than_60, validate_date

medication_router = Router()

from config_data.pagination import MEDICATIONS_PER_PAGE as NOTES_PER_PAGE

def _medication_display_value(value):
    return value if value else t("medication.not_entered")

def _format_course_added(medication_name, dosage, frequency, notes, start_date, end_date):
    return t(
        "medication.course_added",
        medication_name=_medication_display_value(medication_name),
        dosage=_medication_display_value(dosage),
        frequency=_medication_display_value(frequency),
        notes=_medication_display_value(notes),
        start_date=_medication_display_value(start_date),
        end_date=_medication_display_value(end_date),
    )

@medication_router.callback_query(F.data == 'medication')
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        t("menu.medication"),
        reply_markup=get_medication_sumbenu()
    )
    await callback.answer()

@medication_router.callback_query(F.data == "add_medication")
async def process_add_medication(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MedicationCourse.medication_name)
    await callback.message.answer(t("medication.name_prompt"), reply_markup=get_cancel_kb())

@medication_router.message(StateFilter(MedicationCourse.medication_name))
async def process_medication_name(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    if validate_less_than_40(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'medication_name', message.text)
            await message.answer(t("medication.name_updated", value=message.text))
            await state.clear()
            return
        await state.update_data(medication_name=message.text)
        await state.set_state(MedicationCourse.dosage)
        await message.answer(
            t("medication.dosage_prompt", hint=t("medication.dosage_too_long")),
            reply_markup=get_cancel_kb(),
        )
    else:
        await message.answer(t("medication.name_too_long"), reply_markup=get_cancel_kb())

@medication_router.message(StateFilter(MedicationCourse.dosage))
async def process_medication_dosage(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    if validate_less_than_40(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'dosage', message.text)
            await message.answer(t("medication.dosage_updated", value=message.text))
            await state.clear()
            return
        await state.update_data(dosage=message.text)
        await state.set_state(MedicationCourse.frequency)
        await message.answer(
            t("medication.frequency_prompt", hint=t("medication.frequency_too_long")),
            reply_markup=get_cancel_kb(),
        )
    else:
        await message.answer(t("medication.dosage_too_long"), reply_markup=get_cancel_kb())

@medication_router.message(StateFilter(MedicationCourse.frequency))
async def process_medication_frequency(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    if validate_less_than_40(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'frequency', message.text)
            await message.answer(t("medication.frequency_updated", value=message.text))
            await state.clear()
            return
        await state.update_data(frequency=message.text)
        await state.set_state(MedicationCourse.notes)
        await message.answer(
            t("medication.notes_prompt", hint=t("medication.notes_too_long")),
            reply_markup=get_skip_cancel_buttons(),
        )
    else:
        await message.answer(t("medication.frequency_too_long"), reply_markup=get_cancel_kb())

@medication_router.callback_query(F.data == 'skip_note_for_medication', StateFilter(MedicationCourse.notes))
async def process_medication_notes(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MedicationCourse.start_date)
    await callback.message.answer(t("medication.start_date_prompt"), reply_markup=get_cancel_kb())
    await callback.answer()

@medication_router.message(StateFilter(MedicationCourse.notes))
async def process_medication_notes(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    if validate_less_than_60(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'notes', message.text)
            await message.answer(t("medication.notes_updated", value=message.text))
            await state.clear()
            return
        await state.update_data(notes=message.text)
        await state.set_state(MedicationCourse.start_date)
        await message.answer(t("medication.start_date_prompt"), reply_markup=get_cancel_kb())
    else:
        await message.answer(t("medication.notes_too_long"), reply_markup=get_cancel_kb())

@medication_router.message(StateFilter(MedicationCourse.start_date))
async def process_medication_start_date(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    if validate_date(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            prof_start_date_dt = datetime.strptime(message.text, "%Y-%m-%d")
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'start_date', prof_start_date_dt)
            await message.answer(t("medication.start_date_updated", value=message.text))
            await state.clear()
            return
        await state.update_data(start_date=message.text)
        await state.set_state(MedicationCourse.end_date)
        await message.answer(
            t("medication.end_date_create_prompt", hint=t("medication.start_date_invalid")),
            reply_markup=get_actual_med_cancel_buttons(),
        )
    else:
        await message.answer(t("medication.start_date_invalid"), reply_markup=get_cancel_kb())

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
    text = _format_course_added(medication_name, dosage, frequency, notes, start_date, end_date)
    await state.clear()
    await callback.message.answer(text)
    await callback.answer()

@medication_router.message(StateFilter(MedicationCourse.end_date))
async def process_medication_end_date(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    if validate_date(message.text):
        data = await state.get_data()
        mode = data.get("mdcmode", "create")
        if mode == 'mdc_prof_edit':
            profile_id=data['profile_id']
            mdc_id=data['mdc_id']
            prof_end_date_dt = datetime.strptime(message.text, "%Y-%m-%d")
            await orm_update_medication_attribute(db, int(profile_id), int(mdc_id), 'end_date', prof_end_date_dt)
            await message.answer(t("medication.end_date_updated", value=message.text))
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
        text = _format_course_added(medication_name, dosage, frequency, notes, start_date, end_date)
        await state.clear()
        await message.answer(text)
    else:
        await message.answer(t("medication.start_date_invalid"), reply_markup=get_cancel_kb())

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
        await callback.message.answer(t("medication.no_courses"))
    text = t("medication.courses_list_header", count=len(profile_medications))
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
        await callback.message.answer(t("medication.no_courses"))
    text = t("medication.courses_list_header", count=len(profile_medications))
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
        await message.answer(t("medication.record_not_found"))
        return
    text = t(
        "medication.course_settings",
        profile_name=profile_id.split('|')[1],
        medication_name=profile_mdc.medication_name,
        dosage=profile_mdc.dosage,
        frequency=profile_mdc.frequency,
        notes=t("seizure.not_filled") if profile_mdc.notes is None else profile_mdc.notes,
        start_date=profile_mdc.start_date,
        end_date=t("medication.not_entered") if profile_mdc.end_date is None else profile_mdc.end_date,
        mdc_id=profile_mdc.id,
    )
    await message.answer(text)

@medication_router.message(F.text.startswith('/mdc'))
async def process_editing_medication_settings(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, action, mdc_id = message.text.split('_', 2)
    profile_id = await get_cached_current_profile(db, message.chat.id)
    profile_mdc = await orm_get_profile_medication_by_id(db, int(profile_id.split('|')[0]), int(mdc_id))
    if profile_mdc is None:
        await message.answer(t("medication.record_not_found"))
        return
    await state.update_data(mdcmode="mdc_prof_edit", profile_id=profile_id.split('|')[0], mdc_id=mdc_id)
    if action == "medname":
        await message.answer(t("medication.name_prompt"))
        await state.set_state(MedicationCourse.medication_name)
    elif action == "dos":
        await message.answer(t("medication.dosage_prompt", hint=t("medication.dosage_too_long")))
        await state.set_state(MedicationCourse.dosage)
    elif action == "freq":
        await message.answer(t("medication.frequency_prompt", hint=t("medication.frequency_too_long")))
        await state.set_state(MedicationCourse.frequency)
    elif action == "note":
        await message.answer(t("medication.notes_edit_prompt", hint=t("medication.notes_too_long")))
        await state.set_state(MedicationCourse.notes)
    elif action == 'strdt':
        await message.answer(t("medication.start_date_prompt"))
        await state.set_state(MedicationCourse.start_date)
    elif action == 'enddt':
        await message.answer(t("medication.end_date_prompt"))
        await state.set_state(MedicationCourse.end_date)
    elif action == 'del':
        await message.answer(t("medication.delete_confirm"), reply_markup=get_deleting_medication_kb(mdc_id, int(profile_id.split('|')[0])))
    else:
        await message.answer(t("medication.unknown_command"))

@medication_router.callback_query(F.data.startswith("delete_med_prof"))
async def process_confirm_deleting_notify(callback: CallbackQuery, db: AsyncSession):
    _, answer, mdc_id, prof_id = callback.data.split(':', 3)
    if answer == 'yes':
        print('yes')
        res = await orm_delete_profile_medication(db, int(prof_id), int(mdc_id))
        print('res')
        if res:
            await callback.message.answer(t("medication.delete_success"))
        else:
            await callback.message.answer(t("medication.record_not_found"))
    else:
        await callback.message.answer(t("medication.delete_cancelled"))
    await callback.answer()
