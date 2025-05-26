from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram import Bot

from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from filters.correct_commands import ProfileIsSetCb
from handlers_logic.states_factories import SeizureForm
from handlers_logic.seizure_form_logic import (
    ask_for_a_year, handle_severity, handle_duration_by_message, handle_comment, handle_day,
    handle_short_date, handle_date_by_message, handle_skip_step, handle_time_of_date_message,
    handle_time_by_btns, handle_month_of_date, handle_count_by_message, handle_count_of_seizures,
    handle_toggle_trigger, handle_triggers_page, handle_save_toggled_triggers,
    handle_triggers_by_message, handle_seizre_right_now, handle_stop_tracking_duration,
    handle_duration_by_cb, handle_geolocation, handle_video, handle_location_by_message
)
from database.orm_query import orm_add_new_seizure
from keyboards.seizure_kb import get_seizure_timing
from services.redis_cache_data import get_cached_current_profile, get_cached_login
from services.note_format import get_formatted_seizure_info, get_minutes_and_seconds
seizures_router = Router()

def get_seizure_info_dict(seizure_data: dict):
    seizure_data_dict = {}
    default_values = {
        "date_short": "Не заполнено",
        "year": "Не заполнено",
        "month": "Не заполнено",
        "day": "Не заполнено",
        "time_of_day": None,
        "type_of_seizure": None,
        "selected_triggers": None,
        "count": None,
        "triggers": None,
        "severity": None,
        "duration": None,
        "comment": None,
        "symptoms": None,
        "video_tg_id": None,
        "location": None,
    }
    for key, default_value in default_values.items():
        seizure_data_dict[key] = seizure_data.get(key, default_value)
    return seizure_data_dict

@seizures_router.callback_query(F.data == "skip_step")
async def process_skip_step(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_skip_step(callback.message, state)
    await callback.answer()

@seizures_router.callback_query(F.data ==  "fix_seizure")
async def process_right_now_or_passed(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    text = (
        "Приступ происходит прямо сейчас или вы хотите зафиксировать его постфактум?\n\n"

        "Если выбрать фиксацию в реальном времени, начнётся автоматический отсчёт продолжительности приступа, и дата с временем будут установлены автоматически.\n"

        "Если же вы фиксируете приступ задним числом, вы сможете вручную указать все данные.\n"
    )
    await callback.message.edit_text(text, reply_markup=get_seizure_timing())

@seizures_router.callback_query(F.data == "check_input_seizure_data")
async def process_display_of_input_seizure_data(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    seizure_data = await state.get_data()
    login = await get_cached_login(db, callback.message.chat.id)
    if not seizure_data:
        await callback.message.answer("Начните заполнение данных о приступе заново.")
        await callback.answer()
        return
    current_profile = await get_cached_current_profile(db, callback.message.chat.id)
    if 'date_short' in seizure_data:
        date = seizure_data['date_short']
    else:
        date = f"{seizure_data.get('year', 'Не заполнено')}-{seizure_data.get('month', 'Не заполнено')}-{seizure_data.get('day', 'Не заполнено')}"

    time_of_day = seizure_data.get('time_of_day', None)
    list_of_triggers = seizure_data.get('selected_triggers', None)
    count = seizure_data.get('count', None)
    triggers = seizure_data.get('triggers', None)
    severity = seizure_data.get('severity', None)
    duration = seizure_data.get('duration', None)
    comment = seizure_data.get('comment', None)
    symptoms = seizure_data.get('symptoms', None)
    video_tg_id = seizure_data.get('video_tg_id', None)
    location = seizure_data.get('location', None)
    location_by_message = seizure_data.get('location_by_message', None)

    if current_profile == None:
        await callback.message.answer("Выберите профиль в основном меню.")
    if list_of_triggers and triggers == None:
        triggers = ", ".join(list_of_triggers)

    await get_formatted_seizure_info(
        seizure_id = 0,
        current_profile = current_profile.split('|', 1)[1],
        date = date,
        time = time_of_day,
        count = count,
        triggers = triggers,
        severity = severity,
        duration = get_minutes_and_seconds(duration),
        comment = comment,
        symptoms = symptoms,
        video_tg_id = video_tg_id,
        location = f"{location if location is not None else ''}"+f"{location_by_message if location_by_message is not None else ''}",
        bot = bot,
        message = callback.message
    )
    await orm_add_new_seizure(
        db,
        int(current_profile.split("|")[0]),
        date,
        time_of_day,
        severity,
        duration,
        comment,
        count,
        video_tg_id,
        triggers,
        f"{location if location is not None else ''}"+f"{location_by_message if location_by_message is not None else ''}",
        symptoms,
        creator_login = login
    )
    await callback.answer()
    await state.clear()

@seizures_router.callback_query(F.data == "seizure_right_now", ProfileIsSetCb())
async def process_seizre_right_now(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_seizre_right_now(callback.message, state, db)
    await callback.answer()

@seizures_router.callback_query(F.data == "stop_track_duration")
async def process_stop_tracking_duration(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_stop_tracking_duration(callback.message, state)
    await callback.answer()

@seizures_router.callback_query(F.data.startswith("seizure_passed"), ProfileIsSetCb())
async def start_fix_seizure(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(start_fix=True)
    await ask_for_a_year(callback.message, state)
    await state.set_state(SeizureForm.year)
    await callback.answer()

@seizures_router.callback_query(F.data.startswith("year"), StateFilter(SeizureForm.year))
async def process_date_short(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_short_date(callback, state, db)

@seizures_router.message(StateFilter(SeizureForm.year))
async def process_year_by_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_date_by_message(message, state, db)

def format_small_date_numbers(date: str) -> str:
    if int(date) < 10 and int(date) > 0:
        return f"0{int(date)}"
    else:
        return date

@seizures_router.callback_query(F.data.startswith('month'), StateFilter(SeizureForm.month))
async def process_month_of_date(callback: CallbackQuery, state: FSMContext):
    await handle_month_of_date(callback, state)

@seizures_router.callback_query(F.data.startswith('day'), StateFilter(SeizureForm.day))
async def process_day_of_date(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_day(callback, state, db)

@seizures_router.message(StateFilter(SeizureForm.hour))
async def process_time_of_date_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_time_of_date_message(message, state, db)

@seizures_router.callback_query(F.data.startswith('time_range'), StateFilter(SeizureForm.hour))
async def process_time_by_btns(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_time_by_btns(callback, state, db)

@seizures_router.callback_query(F.data.startswith('count_of_seizures'), StateFilter(SeizureForm.count))
async def process_count_of_seizures(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_count_of_seizures(callback, state, db)

@seizures_router.message(StateFilter(SeizureForm.count))
async def process_count_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_count_by_message(message, state, db)

@seizures_router.callback_query(F.data.startswith('toggle'), StateFilter(SeizureForm.triggers))
async def process_toggle_trigger(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_toggle_trigger(callback, state, db)

@seizures_router.callback_query(F.data.startswith('page'), StateFilter(SeizureForm.triggers))
async def process_triggers_page(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_triggers_page(callback, state, db)

@seizures_router.callback_query(F.data.startswith('done'), StateFilter(SeizureForm.triggers))
async def process_save_toggled_triggers(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_save_toggled_triggers(callback, state, db)

@seizures_router.message(StateFilter(SeizureForm.triggers))
async def process_triggers_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_triggers_by_message(message, state, db)

@seizures_router.callback_query(F.data.startswith('saverity'), StateFilter(SeizureForm.severity))
async def process_severity_message(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_severity(callback, state, db)

@seizures_router.callback_query(F.data.startswith('seizure_duration'), StateFilter(SeizureForm.duration))
async def process_duration_cb(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_duration_by_cb(callback, state, db)
    await callback.answer()

@seizures_router.message(StateFilter(SeizureForm.duration))
async def process_duration_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_duration_by_message(message, state, db)

@seizures_router.message(StateFilter(SeizureForm.comment))
async def process_comment_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_comment(message, state, db)

@seizures_router.message((F.video) | (F.document) | (F.video_note), StateFilter(SeizureForm.video_tg_id))
async def process_video(message: Message, state: FSMContext, db: AsyncSession):
    await handle_video(message, state, db)

@seizures_router.message(F.location, StateFilter(SeizureForm.location))
async def process_location_of_seizure(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    await handle_geolocation(message, state, db, bot)

@seizures_router.message(StateFilter(SeizureForm.location))
async def process_location_by_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_location_by_message(message, state, db)