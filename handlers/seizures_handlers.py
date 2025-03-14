from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Seizure
from keyboards.seizure_kb import get_year_date_kb, get_month_date_kb, get_day_kb, get_times_of_day_kb
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
async def process_display_of_input_seizure_data(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
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

    message_text = (
        "Введенные данные о приступе:\n"
        f"Дата: {date}\n"
        f"Час: {time_of_day}\n"
        f"Количество: {count}\n"
        f"Триггеры: {triggers}\n"
        f"Тяжесть: {severity}\n"
        f"Продолжительность (в минутах): {duration}\n"
        f"Комментарий: {comment}\n"
        f"Симптомы: {symptoms}\n"
        f"Видео: {video_tg_id}\n"
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
        video_tg_id =  None if video_tg_id else video_tg_id,
        triggers = triggers,
        location = location,
        symptoms = symptoms
    )
    db.add(new_seizure)
    await callback.message.answer(message_text)
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

@seizures_router.callback_query(F.data.startswith('month'), StateFilter(SeizureForm.month))
async def process_month_of_date(callback: CallbackQuery, state: FSMContext):
    _, month_index, month_name = callback.data.split(':', 2)
    print("Пойман")
    await state.update_data(month=month_index)
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
    await state.update_data(day=day_index)
    await state.set_state(SeizureForm.hour)
    await callback.message.edit_text(f"Выбрано число: {day_index}", reply_markup=get_times_of_day_kb())

@seizures_router.callback_query(F.data.startswith('time_of_day'),
                                StateFilter(SeizureForm.hour))
async def process_times_of_day(callback: CallbackQuery, state: FSMContext):
    _, time_of_day = callback.data.split(':', 1)
    await state.update_data(time_of_day=time_of_day)
    await state.set_state(SeizureForm.count)
    await callback.message.edit_text(f"Выбрано время суток {time_of_day}")