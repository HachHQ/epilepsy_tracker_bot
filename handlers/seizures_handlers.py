from aiogram import Router, F
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputMediaAudio,
                           InputMediaDocument, InputMediaPhoto,
                           InputMediaVideo, Message)
from aiogram import Bot

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Seizure
from keyboards.seizure_kb import get_year_date_kb, get_month_date_kb, get_day_kb, get_times_of_day_kb, get_video_tg_id_kb
from services.redis_cache_data import get_cached_current_profile

seizures_router = Router()

class SeizureForm(StatesGroup):
    date = State()
    year = State()
    month = State()
    day = State()
    hour = State()
    count = State()
    triggers = State()
    #minutes_range = State()
    severity = State()
    duration = State()
    comment = State()
    symptoms = State()
    video_tg_id = State()
    location = State()


@seizures_router.callback_query(F.data == "check_input_seizure_data")
async def process_display_of_input_seizure_data(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    seizure_data = await state.get_data()
    if not seizure_data:
        await callback.message.answer("Начните заполнение данных о приступе заново.")
        await callback.answer()
        return
    current_profile = await get_cached_current_profile(callback.message.chat.id)
    if 'date_short' in seizure_data:
        date = seizure_data['date_short']
    else:
        date = f"{seizure_data.get('year', 'Не заполнено')}-{seizure_data.get('month', 'Не заполнено')}-{seizure_data.get('day', 'Не заполнено')}"
    time_of_day = seizure_data.get('time_of_day', 'Не заполнено')
    count = seizure_data.get('count', 'Не заполнено')
    triggers = seizure_data.get('triggers', 'Не заполнено')
    severity = seizure_data.get('severity', 'Не заполнено')
    duration = seizure_data.get('duration', 'Не заполнено')
    comment = seizure_data.get('comment', 'Не заполнено')
    symptoms = seizure_data.get('symptoms', 'Не заполнено')
    video_tg_id = seizure_data.get('video_tg_id', 'Не заполнено')
    location = seizure_data.get('location', 'Не заполнено')

    current_profile = await get_cached_current_profile(callback.message.chat.id)

    message_text = (
        f"Введенные данные о приступе для профиля <u>{current_profile.split('|')[1]}</u>:\n"
        f"Дата: {date}\n"
        f"Час: {time_of_day}\n"
        f"Количество: {count}\n"
        f"Триггеры: {triggers}\n"
        f"Тяжесть: {severity}\n"
        f"Продолжительность (в минутах): {duration}\n"
        f"Комментарий: {comment}\n"
        f"Симптомы: {symptoms}\n"
        f"Видео: {"✅" if video_tg_id != "Не заполнено" else video_tg_id}\n"
        f"Место: {location}"
    )


    new_seizure = Seizure(
        profile_id = int(current_profile.split("|")[0]),
        date = date,
        time = time_of_day,
        severity = severity,
        duration = 0 if duration else duration,
        comment = comment,
        count = None if count else count,
        video_tg_id = video_tg_id if video_tg_id else None,
        triggers = triggers,
        location = location,
        symptoms = symptoms
    )
    db.add(new_seizure)
    await callback.message.answer(message_text, parse_mode='HTML')
    if video_tg_id != "Не заполнено":
        await bot.send_video(chat_id=callback.message.chat.id, video=seizure_data['video_tg_id'])

    await callback.answer()
    await state.clear()

@seizures_router.callback_query(F.data.startswith("fix_seizure"))
async def start_fix_seizure(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(f"Выберите год или сразу день из преложенных",
                                    reply_markup=get_year_date_kb(3,1))
    await state.set_state(SeizureForm.year)
    await callback.answer()

@seizures_router.callback_query(F.data.startswith("year"), StateFilter(SeizureForm.year))
async def process_date_short(callback: CallbackQuery, state: FSMContext):
    _, year = callback.data.split(":", 1)
    if year.split('/', 1)[0] == "two_d_ago":
        await state.update_data(date_short=year.split('/', 1)[1])
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text("Выберите время суток: ", reply_markup=get_times_of_day_kb())
        return
    elif year.split('/', 1)[0] == "one_d_ago":
        await state.update_data(date_short=year.split('/', 1)[1])
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text("Выберите время суток: ", reply_markup=get_times_of_day_kb())
        return
    elif year.split('/', 1)[0] == "today":
        await state.update_data(date_short=year.split('/', 1)[1])
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text("Выберите время суток: ", reply_markup=get_times_of_day_kb())
        return
    else:
        await state.update_data(year=year)
        await state.set_state(SeizureForm.month)
        await callback.message.edit_text(f"Выбран {year} год.\nВыберите месяц:", reply_markup=get_month_date_kb())

def format_small_date_numbers(date: str) -> str:
    if int(date) < 10 and int(date) > 0:
        return f"0{int(date)}"
    else:
        return date

@seizures_router.callback_query(F.data.startswith('month'), StateFilter(SeizureForm.month))
async def process_month_of_date(callback: CallbackQuery, state: FSMContext):
    _, month_index, month_name = callback.data.split(':', 2)
    print("Пойман")
    await state.update_data(month=format_small_date_numbers(month_index))
    year_month = await state.get_data()
    await state.set_state(SeizureForm.day)
    await callback.message.edit_text(f"Выбран месяц {month_name}",
                                     reply_markup=get_day_kb(
                                        int(year_month['year']),
                                        int(year_month['month']))
                                     )

@seizures_router.callback_query(F.data.startswith('day'), StateFilter(SeizureForm.day))
async def process_day_of_date(callback: CallbackQuery, state: FSMContext):
    _, day_index = callback.data.split(':', 1)
    await state.update_data(day=format_small_date_numbers(day_index))
    await state.set_state(SeizureForm.video_tg_id)
    await callback.message.edit_text(f"Выбрано число: {day_index}", reply_markup=get_times_of_day_kb())

# @seizures_router.callback_query(F.data.startswith('time_of_day'),
#                                 StateFilter(SeizureForm.hour))
# async def process_times_of_day(callback: CallbackQuery, state: FSMContext):
#     _, time_of_day = callback.data.split(':', 1)
#     await state.update_data(time_of_day=time_of_day)
#     await state.set_state(SeizureForm.count)
#     await callback.message.edit_text(f"Выбрано время суток {time_of_day}")



@seizures_router.message((F.video) | (F.document), StateFilter(SeizureForm.video_tg_id))
async def receive_file_id(message: Message, state: FSMContext, bot: Bot):
    if message.voice:
        print("voice_id", end=' - ')
        print(message.voice.file_id)

    elif message.photo:
        print("photo_id", end=' - ')
        print(message.photo[0].file_id)

    elif message.video:
        await state.update_data(video_tg_id=message.video.file_id)
        await state.update_data(message_video_id=message.message_id)
        await message.answer("Видео сохранено", reply_markup=get_video_tg_id_kb())
        #data = await state.get_data()
        #await bot.send_video(chat_id=message.chat.id, video=data['video_tg_id'], caption="Описание")
        #await bot.send_message(chat_id=message.chat.id, text="Описание", reply_to_message_id=data['message_video_id'])
        print("video_tg_id", end=' - ')
        print(message.video.file_id)

    elif message.animation:
        print("animation_id", end=' - ')
        print(message.animation.file_id)

    elif message.document:
        print("document_id", end=' - ')
        print(message.document.file_id)

    elif message.audio:
        print("audio_id", end=' - ')
        print(message.audio.file_id)