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

from handlers_logic.states_factories import SeizureForm
from handlers_logic.seizure_form_logic import (
    ask_for_a_year, handle_severity, handle_duration, handle_comment, handle_day,
    handle_short_date, handle_date_by_message
)
from database.orm_query import orm_add_new_seizure, orm_update_seizure
from keyboards.seizure_kb import (get_year_date_kb, get_month_date_kb, get_day_kb,
                                 get_severity_kb, get_temporary_cancel_submit_kb, generate_features_keyboard,
                                 get_count_of_seizures_kb, get_duration_kb)
from services.redis_cache_data import get_cached_current_profile
from services.note_format import get_formatted_seizure_info
from services.validators import validate_date, validate_time, validate_count_of_seizures, validate_triggers_list

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

@seizures_router.callback_query(F.data == "check_input_seizure_data")
async def process_display_of_input_seizure_data(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    seizure_data = await state.get_data()
    print(get_seizure_info_dict(seizure_data=seizure_data))
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

    if current_profile == None:
        await callback.message.answer("Выберите профиль в основном меню.")
    if list_of_triggers and triggers == None:
        triggers = ", ".join(list_of_triggers)

    message_text = get_formatted_seizure_info(
        seizure_id=0,
        current_profile = current_profile.split('|', 1)[1],
        date = date,
        time = time_of_day,
        count = count,
        triggers = triggers,
        severity = severity,
        duration = duration,
        comment = comment,
        symptoms = symptoms,
        video_tg_id = video_tg_id,
        location = location,
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
        location,
        symptoms
    )
    await callback.message.answer(message_text, parse_mode='HTML')
    if video_tg_id != None:
        await bot.send_video(chat_id=callback.message.chat.id, video=seizure_data['video_tg_id'])

    await callback.answer()
    await state.clear()

@seizures_router.callback_query(F.data.startswith("fix_seizure"))
async def start_fix_seizure(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await ask_for_a_year(callback.message)
    await state.set_state(SeizureForm.year)
    await callback.answer()

@seizures_router.callback_query(F.data.startswith("year"), StateFilter(SeizureForm.year))
async def process_date_short(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_short_date(callback, state, db)

@seizures_router.message(StateFilter(SeizureForm.year))
async def process_year_by_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_date_by_message(message, state, db)
    # if validate_date(message.text):
    #     await state.update_data(date_short=message.text)
    #     await state.set_state(SeizureForm.hour)
    #     await message.answer("Введите примерное время в которое произошел приступ в формате ЧАС:МИНУТЫ", reply_markup=get_temporary_cancel_submit_kb())
    # else:
    #     await message.answer("<u>Введите дату в формате ГОД-МЕСЯЦ-ДЕНЬ\nНапример: 2020-02-01</u>", parse_mode="HTML", reply_markup=get_temporary_cancel_submit_kb())

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
async def process_day_of_date(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_day(callback, state, db)

@seizures_router.message(StateFilter(SeizureForm.hour))
async def process_time_of_date_message(message: Message, state: FSMContext):
    if validate_time(message.text):
        await state.update_data(time_of_day=message.text)
        print(message.text)
        await state.set_state(SeizureForm.count)
        await message.answer("Введите количество приступов: ", reply_markup=get_count_of_seizures_kb())
    else:
        await message.answer("<u>Время приступа должно быть в формате ЧАСЫ:МИНУТЫ\nНапример: 23:29</u>", reply_markup=get_temporary_cancel_submit_kb(), parse_mode='HTML')

@seizures_router.callback_query(F.data.startswith('count_of_seizures'), StateFilter(SeizureForm.count))
async def process_count_of_seizures(callback: CallbackQuery, state: FSMContext):
    _, count_of_seizures = callback.data.split(':', 1)
    await state.update_data(count=count_of_seizures)
    await state.set_state(SeizureForm.triggers)
    await state.update_data(selected_triggers=[], current_page=0)
    await callback.message.answer("Введите возможные триггеры через запятую: ", reply_markup=generate_features_keyboard([], 0, 5))
    await callback.answer()


@seizures_router.message(StateFilter(SeizureForm.count))
async def process_count_message(message: Message, state: FSMContext):
    if validate_count_of_seizures(message.text):
        await state.update_data(count=message.text)
        await state.set_state(SeizureForm.triggers)
        await state.update_data(selected_triggers=[], current_page=0)
        await message.answer("Выберите или введите возможные триггеры: ", reply_markup=generate_features_keyboard([], 0, 5))
    else:
        await message.answer("<u>Количество приступов должно быть любым не отрицательным числом\nНапример: 0 или 5</u>", parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb())


@seizures_router.callback_query(F.data.startswith('toggle'), StateFilter(SeizureForm.triggers))
async def process_toggle_trigger(callback: CallbackQuery, state: FSMContext):
    _, feature, current_page = callback.data.split(':', 2)

    data = await state.get_data()
    selected_triggers = data.get("selected_triggers", [])
    if feature in selected_triggers:
        selected_triggers.remove(feature)
    else:
        selected_triggers.append(feature)
    await state.update_data(selected_triggers=selected_triggers)
    await callback.message.edit_text('Выберите или введите возможные триггеры: ',
        reply_markup=generate_features_keyboard(selected_triggers, current_page, 5)
    )
    await callback.answer()

@seizures_router.callback_query(F.data.startswith('page'), StateFilter(SeizureForm.triggers))
async def process_triggers_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_triggers = data.get("selected_triggers", [])
    print(callback.data)
    new_page = callback.data.split(':', 1)[1]

    await state.update_data(current_page=new_page)
    await callback.message.edit_text('Выберите или введите возможные триггеры: ',
        reply_markup=generate_features_keyboard(selected_triggers, int(new_page), 5)
    )
    await callback.answer()

@seizures_router.callback_query(F.data.startswith('done'), StateFilter(SeizureForm.triggers))
async def process_save_toggled_triggers(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_triggers = data.get("selected_triggers", [])
    if selected_triggers:
        await state.set_state(SeizureForm.severity)
        print(selected_triggers)
        await callback.message.edit_text("Оцените степень тяжести приступа от 1 до 10: ", reply_markup=get_severity_kb())
    else:
        await state.update_data(selected_triggers=[])
        await state.set_state(SeizureForm.severity)
        print(selected_triggers)
        await callback.message.edit_text("Оцените степень тяжести приступа от 1 до 10: ", reply_markup=get_severity_kb())
    await callback.answer()

@seizures_router.message(StateFilter(SeizureForm.triggers))
async def process_triggers_message(message: Message, state: FSMContext):
    if validate_triggers_list(message.text):
        print('триггер')
        await state.update_data(triggers=message.text)
        await state.set_state(SeizureForm.severity)
        await message.answer("Оцените степень тяжести приступа от 1 до 10: ", reply_markup=get_severity_kb())
    else:
        await message.answer("<u>Список не должен быть длиннее 250 символов</u>", parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb())

@seizures_router.callback_query(F.data.startswith('saverity'), StateFilter(SeizureForm.severity))
async def process_severity_message(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await handle_severity(callback, state, db)

@seizures_router.message(StateFilter(SeizureForm.duration))
async def process_duration_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_duration(message, state, db)

@seizures_router.message(StateFilter(SeizureForm.comment))
async def process_comment_message(message: Message, state: FSMContext, db: AsyncSession):
    await handle_comment(message, state, db)

@seizures_router.message((F.video) | (F.document) | (F.video_note), StateFilter(SeizureForm.video_tg_id))
async def receive_file_id(message: Message, state: FSMContext):
    if message.video:
        await state.update_data(video_tg_id=message.video.file_id)
        await state.update_data(message_video_id=message.message_id)
        await message.answer("Видео сохранено", reply_markup=get_temporary_cancel_submit_kb())
        await message.answer("Нажмите на кнопку 'Подтвердить', чтобы и сохранить данные о приступе в базе данных.")
    elif message.video_note:
        print("Кружок")
        print(video_tg_id=message.video_note.file_unique_id)
    else:
        await message.answer("Пришилите видео приступа: ", reply_markup=get_temporary_cancel_submit_kb())
