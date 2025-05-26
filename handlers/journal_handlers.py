from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from filters.correct_commands import ProfileIsSetCb
from handlers_logic.states_factories import SeizureForm
from handlers_logic.seizure_form_logic import ask_for_a_year
from database.orm_query import orm_get_seizures_by_profile_descending, orm_get_seizure_info, orm_delete_seizure
from services.redis_cache_data import get_cached_current_profile, get_cached_login
from services.note_format import get_formatted_seizure_info, get_minutes_and_seconds
from keyboards.journal_kb import get_nav_btns_of_list_of_seizures, get_journal_nav_kb
from keyboards.seizure_kb import (
    get_year_date_kb, get_severity_kb, get_time_ranges_kb, get_count_of_seizures_kb,
    generate_features_keyboard, get_duration_kb
)
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb
journal_router = Router()

NOTES_PER_PAGE = 8

def sort_seizures_by_datetime(seizures):
    def get_datetime(item):
        date_str = item.date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if hasattr(item, 'time') and item.time:
            time_str = item.time
            datetime_obj = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        else:
            datetime_obj = date_obj

        return datetime_obj
    sorted_data = sorted(seizures, key=get_datetime, reverse=True)
    return sorted_data

def display_seizure_notes(seizures, current_page, login):
    seizures_sorted_by_datetime = sort_seizures_by_datetime(seizures)
    current_page = int(current_page)
    start_index = current_page * NOTES_PER_PAGE
    end_index = int(start_index) + NOTES_PER_PAGE
    seizures_on_page = seizures_sorted_by_datetime[start_index:end_index]
    text = ""
    for seizure in seizures_on_page:
        line = (
            f"{seizure.date} "
            f"{seizure.time + " "  if seizure.time is not None else ""}"
            f"{seizure.creator_login + " " if seizure.creator_login is not None and seizure.creator_login != login else ""}"
            f"/show_{seizure.id}\n\n"
        )
        text += line
    return text

@journal_router.callback_query(F.data == "seizure_data")
async def process_journal_handler(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.message.edit_text("Выберите, что просмотреть: журнал, графики или статистику", reply_markup=get_journal_nav_kb())

@journal_router.callback_query(F.data == "journal", ProfileIsSetCb())
async def get_list_of_seizures(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    login = await get_cached_login(db, callback.message.chat.id)
    print(callback.message.chat.id)
    current_profile_id = await get_cached_current_profile(db, callback.message.chat.id)
    if current_profile_id is None:
        await callback.message.answer("Выберите профиль для просмотра журнала")
        return
    seizures = await orm_get_seizures_by_profile_descending(db, int(current_profile_id.split('|', 1)[0]))
    if not seizures:
        await callback.message.answer(f"Для профиля _{current_profile_id.split('|', 1)[1]}_ нет зафиксированных приступов", parse_mode='MarkDownV2')
        await callback.answer()
        return
    text = f"Зафиксированные приступы для профиля <u>{current_profile_id.split('|', 1)[1]}</u>\n\n"
    text += display_seizure_notes(seizures, 0, login)
    await callback.message.answer(f"{text}", parse_mode='HTML', reply_markup=get_nav_btns_of_list_of_seizures(len(seizures), NOTES_PER_PAGE, 0))
    await callback.answer()

@journal_router.callback_query(F.data.startswith('journal_page'))
async def process_pagination_of__seizures_list(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    login = await get_cached_login(db, callback.message.chat.id)
    _, page = callback.data.split(':', 1)
    current_profile_id = await get_cached_current_profile(db, callback.message.chat.id)
    seizures = await orm_get_seizures_by_profile_descending(db, int(current_profile_id.split('|', 1)[0]))
    text = f"Зафиксированные приступы для профиля <u>{current_profile_id.split('|', 1)[1]}</u>\n\n"
    text += display_seizure_notes(seizures, int(page), login)
    await callback.message.edit_text(text, reply_markup=get_nav_btns_of_list_of_seizures(len(seizures), NOTES_PER_PAGE, int(page)), parse_mode='HTML')


@journal_router.message(F.text.startswith('/show'))
async def get_detailed_info_about_seizure(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    await state.clear()
    seizure_id = message.text.split('_', 1)[1]
    if not seizure_id.isnumeric():
        await message.answer("Неверный индекс записи.")
        return
    current_profile = await get_cached_current_profile(db, message.chat.id)
    if current_profile is None:
        await message.answer("Выберите профиль.")
        return
    seizure = await orm_get_seizure_info(db, int(seizure_id), current_profile.split('|', 1)[0])
    if not seizure:
        await message.answer(f'Нет такой записи для профиля {current_profile.split('|', 1)[1]}.')
        return
    print(seizure.location)
    await get_formatted_seizure_info(
        current_profile = current_profile.split('|', 1)[1],
        date = seizure.date,
        time = seizure.time,
        count = seizure.count,
        triggers = seizure.triggers,
        severity = seizure.severity,
        duration = get_minutes_and_seconds(seizure.duration),
        comment = seizure.comment,
        symptoms = seizure.symptoms,
        video_tg_id = seizure.video_tg_id,
        location = seizure.location,
        seizure_id = seizure.id,
        bot = bot,
        message = message
    )

@journal_router.message(F.text.startswith('/edit'))
async def show_edit_options(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    await state.clear()
    seizure_id = int(message.text.split('_', 1)[1])
    current_profile = await get_cached_current_profile(db, message.chat.id)
    seizure = await orm_get_seizure_info(db, int(seizure_id), int(current_profile.split('|', 1)[0]))
    if not seizure:
        await message.answer('Такой записи для вашего профиля нет.')
        return
    await get_formatted_seizure_info(
        seizure_id = seizure.id,
        current_profile = current_profile.split('|', 1)[1],
        date = seizure.date,
        time = seizure.time,
        count = seizure.count,
        triggers = seizure.triggers,
        severity = seizure.severity,
        duration = get_minutes_and_seconds(seizure.duration),
        comment = seizure.comment,
        symptoms = seizure.symptoms,
        video_tg_id = seizure.video_tg_id,
        location = seizure.location,
        edit_mode=True,
        bot = bot,
        message = message
    )
    # await message.answer(text, parse_mode='HTML')

@journal_router.message(F.text.startswith('/update'))
async def get_seizure_info_to_edit(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    await state.clear()
    _, action, seizure_id = message.text.split('_', 2)
    current_profile = await get_cached_current_profile(db, message.chat.id)
    await state.update_data(mode="edit", seizure_id=int(seizure_id), profile_id=int(current_profile.split('|', 1)[0]))
    if action == "date":
        await ask_for_a_year(message, state)
        await state.set_state(SeizureForm.year)
    elif action == "time":
        await message.answer("Выберите или введите время приступа: ", reply_markup=get_time_ranges_kb(action_btns=False))
        await state.set_state(SeizureForm.hour)
    elif action == "count":
        await message.answer("Выберите количество приступов: ", reply_markup=get_count_of_seizures_kb(action_btns=False))
        await state.set_state(SeizureForm.count)
    elif action == "triggers":
        await state.update_data(selected_triggers=[], current_page=0)
        await message.answer("Выберите или введите воможные триггеры: ", reply_markup=generate_features_keyboard([], 0, 5, action_btns=False))
        await state.set_state(SeizureForm.triggers)
    elif action == "severity":
        await message.answer("Выберите степень тяжести:", reply_markup=get_severity_kb(action_btns=False))
        await state.set_state(SeizureForm.severity)
    elif action == "duration":
        await message.answer("Введите примерную продолжительность в минутах: ", reply_markup=get_duration_kb(action_btns=False))
        await state.set_state(SeizureForm.duration)
    elif action == "comment":
        await message.answer("Введите комментарий к приступу: ")
        await state.set_state(SeizureForm.comment)
    elif action == "video":
        await message.answer("Пришлите боту новое видео: ")
        await state.set_state(SeizureForm.video_tg_id)
    elif action == "symptoms":
        await message.answer("Выберите или введите симптомы приступа: ")
        await state.set_state(SeizureForm.symptoms)
    elif action == "location":
        await message.answer("Напишите, где случился приступ или пришлите вашу геолокацию, нажав на кнопку под строкой ввода: ", reply_markup=get_geolocation_for_timezone_kb())
        await state.set_state(SeizureForm.location)


@journal_router.message(F.text.startswith('/delete'))
async def delete_seizure(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    seizure_id = int(message.text.split('_', 1)[1])
    current_profile = await get_cached_current_profile(db, message.chat.id)
    if current_profile is None:
        await message.answer("Выберите профиль.")
        return
    res = await orm_delete_seizure(db, seizure_id, int(current_profile.split('|', 1)[0]))
    if res:
        await message.answer("Запись успешно удалена.")
    else:
        await message.answer("Нет такой записи.")