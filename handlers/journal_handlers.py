import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import Command, StateFilter
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.states_factories import UpdateSeizureAttribute, SeizureForm
from handlers_logic.seizure_form_logic import ask_for_a_year, handle_severity
from handlers.seizures_handlers import start_fix_seizure
from database.orm_query import orm_get_seizures_by_profile_ascending, orm_get_seizures_by_profile_descending, orm_get_seizure_info, orm_delete_seizure
from services.redis_cache_data import get_cached_current_profile
from services.note_format import get_formatted_seizure_info
from keyboards.journal_kb import get_nav_btns_of_list_of_seizures
from keyboards.seizure_kb import (
    get_year_date_kb, get_severity_kb, get_time_ranges_kb, get_count_of_seizures_kb,
    generate_features_keyboard
)
journal_router = Router()

NOTES_PER_PAGE = 8

def display_seizure_notes(seizures, current_page):
    current_page = int(current_page)
    start_index = current_page * NOTES_PER_PAGE
    end_index = int(start_index) + NOTES_PER_PAGE
    seizures_on_page = seizures[start_index:end_index]
    text = ""
    for seizure in seizures_on_page:
        line = (f"{seizure.date}  /show_{seizure.id}\n\n")
        text += line
    return text

@journal_router.callback_query(F.data == "journal")
async def get_list_of_seizures(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    print(callback.message.chat.id)
    current_profile_id = await get_cached_current_profile(db, callback.message.chat.id)
    seizures = await orm_get_seizures_by_profile_descending(db, int(current_profile_id.split('|', 1)[0]))
    if not seizures:
        await callback.message.answer(f"Для профиля _{current_profile_id.split('|', 1)[1]}_ нет зафиксированных приступов", parse_mode='MarkDownV2')
        await callback.answer()
        return
    text = f"Зафиксированные приступы для профиля <u>{current_profile_id.split('|', 1)[1]}</u>\n\n"
    text += display_seizure_notes(seizures, 0)
    await callback.message.answer(f"{text}", parse_mode='HTML', reply_markup=get_nav_btns_of_list_of_seizures(len(seizures), NOTES_PER_PAGE, 0))
    await callback.answer()

@journal_router.callback_query(F.data.startswith('journal_page'))
async def process_pagination_of__seizures_list(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, page = callback.data.split(':', 1)
    current_profile_id = await get_cached_current_profile(db, callback.message.chat.id)
    seizures = await orm_get_seizures_by_profile_descending(db, int(current_profile_id.split('|', 1)[0]))
    text = f"Зафиксированные приступы для профиля <u>{current_profile_id.split('|', 1)[1]}</u>\n\n"
    text += display_seizure_notes(seizures, int(page))
    await callback.message.edit_text(text, reply_markup=get_nav_btns_of_list_of_seizures(len(seizures), NOTES_PER_PAGE, int(page)), parse_mode='HTML')


@journal_router.message(F.text.startswith('/show'))
async def get_detailed_info_about_seizure(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    await state.clear()
    seizure_id = message.text.split('_', 1)[1]
    if not seizure_id.isnumeric():
        await message.answer("Неверный индекс записи.")
        return
    current_profile = await get_cached_current_profile(db, message.chat.id)
    seizure = await orm_get_seizure_info(db, int(seizure_id), current_profile.split('|', 1)[0])
    if not seizure:
        await message.answer(f'Нет такой записи для профиля {current_profile.split('|', 1)[1]}.')
        return
    text = get_formatted_seizure_info(
        current_profile = current_profile.split('|', 1)[1],
        date = seizure.date,
        time = seizure.time,
        count = seizure.count,
        triggers = seizure.triggers,
        severity = seizure.severity,
        duration = seizure.duration,
        comment = seizure.comment,
        symptoms = seizure.symptoms,
        video_tg_id = seizure.video_tg_id,
        location = seizure.location,
        seizure_id = seizure.id
    )
    await message.answer(f"{text}", parse_mode='HTML')
    if seizure.video_tg_id:
        await bot.send_video(chat_id=message.chat.id, video=seizure.video_tg_id)
    if seizure.location:
        await bot.send_location(chat_id=message.chat.id, video=seizure.video_tg_id)

@journal_router.message(F.text.startswith('/edit'))
async def show_edit_options(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    seizure_id = int(message.text.split('_', 1)[1])
    current_profile = await get_cached_current_profile(db, message.chat.id)
    seizure = await orm_get_seizure_info(db, int(seizure_id), int(current_profile.split('|', 1)[0]))
    if not seizure:
        await message.answer('Такой записи для вашего профиля нет.')
        return
    text = get_formatted_seizure_info(
        seizure_id = seizure.id,
        current_profile = current_profile.split('|', 1)[1],
        date = seizure.date,
        time = seizure.time,
        count = seizure.count,
        triggers = seizure.triggers,
        severity = seizure.severity,
        duration = seizure.duration,
        comment = seizure.comment,
        symptoms = seizure.symptoms,
        video_tg_id = seizure.video_tg_id,
        location = seizure.location,
        edit_mode=True
    )
    await message.answer(text, parse_mode='HTML')

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
        await message.answer("Введите примерную продолжительность: ")
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
        await message.answer("Отправьте геолокацию или опишите место, где произошел приступ: ")
        await state.set_state(SeizureForm.location)


@journal_router.message(F.text.startswith('/delete'))
async def delete_seizure(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    seizure_id = int(message.text.split('_', 1)[1])
    current_profile = await get_cached_current_profile(db, message.chat.id)
    res = await orm_delete_seizure(db, seizure_id, int(current_profile.split('|', 1)[0]))
    if res:
        await message.answer("Запись успешно удалена.")
    else:
        await message.answer("Нет такой записи.")