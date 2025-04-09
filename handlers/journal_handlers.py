import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import Command, StateFilter
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_get_seizures_by_profile_ascending, orm_get_seizures_by_profile_descending, orm_get_seizure_info, orm_delete_seizure
from services.redis_cache_data import get_cached_current_profile
from services.note_format import get_formatted_seizure_info, get_formatted_seizure_edit
from keyboards.journal_kb import get_list_of_seizures

journal_router = Router()

class UpdateSeizureAttribute(StatesGroup):
    choose_attribute = State()
    input_new_value = State()

@journal_router.callback_query(F.data == "journal")
async def get_list_of_seizures(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    print(callback.message.chat.id)
    current_profile_id = await get_cached_current_profile(db, callback.message.chat.id)
    seizures = await orm_get_seizures_by_profile_descending(db, int(current_profile_id.split('|', 1)[0]))

    text = f"Зафиксированные приступы для профиля <u>{current_profile_id.split('|', 1)[1]}</u>\n\n"
    for seizure in seizures:
        line = (f"{seizure.date}  /show_{seizure.id}\n\n")
        text += line
    await callback.message.answer(f"{text}", parse_mode='HTML')
    await callback.answer()

@journal_router.message(F.text.startswith('/show'))
async def get_detailed_info_about_seizure(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
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
    await message.answer(text, parse_mode='HTML')
    if seizure.video_tg_id:
        await bot.send_video(chat_id=message.chat.id, video=seizure.video_tg_id)
    if seizure.location:
        await bot.send_location(chat_id=message.chat.id, video=seizure.video_tg_id)

@journal_router.message(F.text.startswith('/edit'))
async def show_edit_options(message: Message, state: FSMContext, db: AsyncSession):
    seizure_id = int(message.text.split('_', 1)[1])
    current_profile = await get_cached_current_profile(db, message.chat.id)
    seizure = await orm_get_seizure_info(db, int(seizure_id), int(current_profile.split('|', 1)[0]))
    if not seizure:
        await message.answer('Такой записи для вашего профиля нет.')
        return
    text = get_formatted_seizure_edit(
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
    )
    await message.answer(text, parse_mode='HTML')

@journal_router.message(F.text.startswith('/update'))
async def get_seizure_info_to_edit(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    await state.clear()
    _, action, seizure_id = message.text.split('_', 2)
    await state.set_state(UpdateSeizureAttribute.choose_attribute)
    if action == "date":
        await message.answer("Введите дату снова ")
    elif action == "time":
        await message.answer("")
    elif action == "count":
        await message.answer("")
    elif action == "triggers":
        await message.answer("")
    elif action == "severity":
        await message.answer("")
    elif action == "duration":
        await message.answer("")
    elif action == "comment":
        await message.answer("")
    elif action == "video":
        await message.answer("")
    elif action == "symptoms":
        await message.answer("")
    elif action == "location":
        await message.answer("")
    current_profile = await get_cached_current_profile(db, message.chat.id)


@journal_router.message(F.text.startswith('/delete'))
async def delete_seizure(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    seizure_id = int(message.text.split('_', 1)[1])
    current_profile = await get_cached_current_profile(db, message.chat.id)
    res = await orm_delete_seizure(db, seizure_id, int(current_profile.split('|', 1)[0]))
    if res:
        await message.answer("Запись успешно удалена.")
    else:
        await message.answer("Нет такой записи.")