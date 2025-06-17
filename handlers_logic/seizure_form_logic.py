from aiogram import Bot
from datetime import datetime, timezone, timedelta
from aiogram.types import (
    CallbackQuery, Message, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database.orm_query import (
    orm_get_user
)
from services.notes_formatters import get_minutes_and_seconds
from services.validators import (
    validate_non_neg_N_num, validate_less_than_250, validate_date,
    validate_time,
)
from database.orm_query import orm_update_seizure
from handlers_logic.states_factories import SeizureForm
from keyboards.seizure_kb import (
    get_year_date_kb, get_month_date_kb, get_day_kb,
    get_severity_kb, get_temporary_cancel_submit_kb, generate_features_keyboard,
    get_count_of_seizures_kb, get_duration_kb, get_time_ranges_kb, get_stop_duration_kb, get_final_seizure_btns
)
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb


async def handle_skip_step(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if (current_state is None) or (str(current_state).split(':', 1)[0] != "SeizureForm"):
        return await message.answer("Начните заполнение заново.")
    if str(current_state).split(':', 1)[0] == "SeizureForm":
        await state.set_state(SeizureForm.next_state(current_state))
        if current_state == "SeizureForm:hour":
            await message.edit_text(f"Выберите или введите примерную продолжительность приступа: ", reply_markup=get_duration_kb())
        elif current_state == "SeizureForm:duration":
            await message.edit_text("Если в рамках одного припадка было несколько приступов, выберите их количество: ", reply_markup=get_count_of_seizures_kb())
        elif current_state == "SeizureForm:count":
            await message.edit_text("Выберите или введите возможные триггеры: ", reply_markup=generate_features_keyboard([], 0, 5))
        elif current_state == "SeizureForm:triggers":
            await message.edit_text("Оцените степень тяжести приступа от 1 до 10: ", reply_markup=get_severity_kb())
        elif current_state == "SeizureForm:severity":
            await message.edit_text("Оставьте комментарий, если это нужно", reply_markup=get_temporary_cancel_submit_kb())
        elif current_state == "SeizureForm:comment":
            await message.edit_text("Пришлите видео приступа. Это может быть кружок или mp4 файл в любом виде: ", reply_markup=get_temporary_cancel_submit_kb())
        elif current_state == "SeizureForm:video_tg_id":
            await message.edit_text("Напишите, в каком месте случился приступ: ", reply_markup=get_temporary_cancel_submit_kb())
            await message.answer("Или пришлите вашу геолокацию (нажмите на кнопку под полем ввода): ", reply_markup=get_geolocation_for_timezone_kb())
        elif current_state == "SeizureForm:location":
            await message.answer("Все параметры заполнены, завершите или отмените заполнение: ", reply_markup=get_final_seizure_btns())



async def get_action_btns_flag(state):
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == "edit":
        return False
    else:
        return True

def parse_callback_data(data: str) -> dict:
    result = {}
    if ":" not in data:
        return {"type": "unknown", "raw": data}
    type_, *rest = data.split(":")
    result["type"] = type_
    if type_ == "year":
        if "/" in rest[0]:
            short_type, date = rest[0].split("/", 1)
            result.update({"value": short_type, "date": date})
        else:
            result["value"] = rest[0]
    elif type_ == "month":
        result["index"] = rest[0]
        result["name"] = rest[1]
    elif type_ == "day":
        result["value"] = rest[0]
    else:
        result["raw"] = data
    return result

def format_small_date_numbers(date: str) -> str:
    if int(date) < 10 and int(date) > 0:
        return f"0{int(date)}"
    else:
        return date

async def handle_seizre_right_now(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    user = await orm_get_user(db, message.chat.id)
    user_tz = user.timezone
    local_user_tz = get_local_time_from_offset(int(user_tz))
    local_date = local_user_tz.date()
    local_time = local_user_tz.time().isoformat(timespec='minutes')

    duration_datetime_flag = str(datetime.now(timezone.utc))
    print(duration_datetime_flag)

    await state.update_data(exact_duration=duration_datetime_flag)
    await state.update_data(date_short=str(local_date))
    await state.update_data(time_of_day=str(local_time))

    await message.answer("Нажмите на 'СТОП', когда приступ закончится", reply_markup=get_stop_duration_kb())

async def handle_stop_tracking_duration(message: Message, state: FSMContext):
    seizure_data = await state.get_data()
    duration_flag_str = seizure_data.get('exact_duration', None)
    print(duration_flag_str)
    if duration_flag_str is None:
        await message.answer("Начните заполнение заново.")

        return
    clean_date_string = duration_flag_str.strip('"')
    print(clean_date_string)
    duration_flag_datetime = datetime.fromisoformat(clean_date_string)
    print(duration_flag_datetime)
    print(datetime.now(timezone.utc))
    duration_diff = datetime.now(timezone.utc) - duration_flag_datetime
    duration_diff = duration_diff.total_seconds()
    print(duration_diff, type(duration_diff))

    await state.update_data(duration=int(duration_diff))
    await message.edit_text("Если в рамках одного припадка была серия приступов, выберите их количество", reply_markup=get_count_of_seizures_kb())
    await message.answer(f"Продолжительность зафиксирована: {get_minutes_and_seconds(duration_diff)}")
    await state.set_state(SeizureForm.count)

async def ask_for_a_year(message: Message, state: FSMContext):
    action_btns_flag = await get_action_btns_flag(state)
    await message.answer(f"Выберите год или сразу день из преложенных\n\n<u>Либо введите дату вручную в формате ГОД-МЕСЯЦ-ДЕНЬ</u>",
                                reply_markup=get_year_date_kb(4,0, action_btns=action_btns_flag),
                                parse_mode='HTML')

async def handle_short_date(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    parsed = parse_callback_data(callback.data)
    action_btns_flag = await get_action_btns_flag(state)
    data = await state.get_data()
    mode = data.get("mode", "create")

    if parsed.get("value") in {"two_d_ago", "one_d_ago", "today"}:

        if mode == "edit":
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'date', parsed["date"])
            await callback.message.answer(f"Дата обновлена: {parsed["date"]}")
            await callback.answer()
            await state.clear()
            return
        else:
            await state.update_data(date_short=parsed["date"])
            await state.set_state(SeizureForm.hour)
            await callback.message.edit_text(
                "Введите примерное время в которое произошел приступ в формате ЧАС:МИНУТЫ",
                reply_markup=get_time_ranges_kb(action_btns=action_btns_flag)
            )
            return
    await state.update_data(year=parsed["value"])
    await state.set_state(SeizureForm.month)
    await callback.message.edit_text(
        f"Выбран {parsed['value']} год.\nВыберите месяц:",
        reply_markup=get_month_date_kb(action_btns=action_btns_flag)
    )

async def handle_month_of_date(callback: CallbackQuery, state: FSMContext):
    _, month_index, month_name = callback.data.split(':', 2)
    action_btns_flag = await get_action_btns_flag(state)
    print(action_btns_flag)
    await state.update_data(month=format_small_date_numbers(month_index))
    year_month = await state.get_data()
    await state.set_state(SeizureForm.day)
    await callback.message.edit_text(
        f"Выбран месяц {month_name}",
        reply_markup=get_day_kb(
            int(year_month['year']),
            int(year_month['month']),
            action_btns=action_btns_flag
        )
    )

async def handle_day(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    day_index = callback.data.split(':', 1)[1]
    data = await state.get_data()
    action_btns_flag = await get_action_btns_flag(state)
    mode = data.get("mode", "create")
    if mode == "edit":
        year = data['year']
        month = data['month']
        new_date = f'{year}-{month}-{day_index}'
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await orm_update_seizure(db, int(seizure_id), int(profile_id), 'date', new_date)
        await callback.message.answer(f"Дата обновлена: {new_date}")
        await callback.answer()
        await state.clear()
    else:
        await state.update_data(day=format_small_date_numbers(day_index))
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text(
            f"Выбрано число: {day_index}\n\nВведите примерное время в которое произошел приступ в формате ЧАС:МИНУТЫ",
            reply_markup=get_time_ranges_kb(action_btns=action_btns_flag)
        )

async def handle_date_by_message(message: Message, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if validate_date(message.text):

        date = message.text
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'date', date)
            await message.answer(f"Дата обновлена: {date}")
            await state.clear()
        else:
            await state.update_data(date_short=date)
            await state.set_state(SeizureForm.hour)
            await message.answer(
                "Введите примерное время в которое произошел приступ в формате ЧАС:МИНУТЫ",
                  reply_markup=get_time_ranges_kb(action_btns=action_btns_flag)
            )
    else:
        await message.answer(
            "<u>Введите дату в формате ГОД-МЕСЯЦ-ДЕНЬ\nНапример: 2020-02-01</u>",
            parse_mode="HTML",
            reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))

async def handle_time_of_date_message(message: Message, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if validate_time(message.text):
        time = message.text
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'time', time)
            await message.answer(f"Время обновлено: {time}")
            await state.clear()
            return
        await state.update_data(time_of_day=time)
        print(message.text)
        await state.set_state(SeizureForm.duration)
        await message.answer(
            f"Введите примерную продолжительность в минутах: ",
            reply_markup=get_duration_kb(action_btns=action_btns_flag)
        )
        # await state.set_state(SeizureForm.duration)
        # await message.answer(
        #     "Если в рамках одного приступа была серия приступов, выберите их количество",
        #     reply_markup=get_count_of_seizures_kb(action_btns=action_btns_flag))
    else:
        await message.answer(
            "<u>Время приступа должно быть в формате ЧАСЫ:МИНУТЫ\nНапример: 23:29</u>",
            reply_markup=get_time_ranges_kb(action_btns=action_btns_flag),
            parse_mode='HTML')

def get_local_time_from_offset(offset_hours: int) -> datetime:
    offset = timezone(timedelta(hours=offset_hours))
    return datetime.now(timezone.utc).astimezone(offset)

def get_time_with_minutes_offset(local_datetime: datetime, offset_minutes) -> datetime:
    return local_datetime - timedelta(minutes=offset_minutes)

async def handle_time_by_btns(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    time_range = callback.data.split(':', 1)[1]
    user = await orm_get_user(db, callback.message.chat.id)
    user_tz = user.timezone
    local_user_tz = get_local_time_from_offset(int(user_tz))
    local_user_tz.time().isoformat(timespec='minutes')
    if time_range == 'now':
        current_time = str(local_user_tz.time().isoformat(timespec='minutes'))
        print(current_time)
        await state.update_data(time_of_day=current_time)
    elif time_range == '5m_ago':
        time_with_offset = str(get_time_with_minutes_offset(local_user_tz, 5).time().isoformat(timespec='minutes'))
        print(time_with_offset)
        await state.update_data(time_of_day=time_with_offset)
    elif time_range == '15m_ago':
        time_with_offset = str(get_time_with_minutes_offset(local_user_tz, 15).time().isoformat(timespec='minutes'))
        print(time_with_offset)
        await state.update_data(time_of_day=time_with_offset)
    elif time_range == '30m_ago':
        time_with_offset = str(get_time_with_minutes_offset(local_user_tz, 30).time().isoformat(timespec='minutes'))
        print(time_with_offset)
        await state.update_data(time_of_day=time_with_offset)
    elif time_range == '1h_ago':
        time_with_offset = str(get_time_with_minutes_offset(local_user_tz, 60).time().isoformat(timespec='minutes'))
        print(time_with_offset)
        await state.update_data(time_of_day=time_with_offset)
    elif time_range == '1p5h_ago':
        time_with_offset = str(get_time_with_minutes_offset(local_user_tz, 90).time().isoformat(timespec='minutes'))
        print(time_with_offset)
        await state.update_data(time_of_day=time_with_offset)
    elif time_range == '2h_ago':
        time_with_offset = str(get_time_with_minutes_offset(local_user_tz, 120).time().isoformat(timespec='minutes'))
        print(time_with_offset)
        await state.update_data(time_of_day=time_with_offset)
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        time = data.get("time_of_day", None)
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await orm_update_seizure(db, int(seizure_id), int(profile_id), 'time', time)
        await callback.message.answer(f"Время обновлено: {time}")
        await callback.answer()
        await state.clear()
        return
    await state.set_state(SeizureForm.duration)
    await callback.message.edit_text(
        f"Введите примерную продолжительность в минутах: ",
        reply_markup=get_duration_kb(action_btns=action_btns_flag)
    )
    await callback.answer()

async def handle_count_of_seizures(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    count_of_seizures = int(callback.data.split(':', 1)[1])
    action_btns_flag = await get_action_btns_flag(state)
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await orm_update_seizure(db, int(seizure_id), int(profile_id), 'count', count_of_seizures)
        await callback.message.answer(f"Количество обновлено: {count_of_seizures}")
        await callback.answer()
        await state.clear()
        return
    await state.update_data(count=count_of_seizures)
    await state.set_state(SeizureForm.triggers)
    await state.update_data(selected_triggers=[], current_page=0)
    await callback.message.edit_text("Введите возможные триггеры через запятую: ", reply_markup=generate_features_keyboard([], 0, 5, action_btns=action_btns_flag))
    await callback.answer()

async def handle_count_by_message(message: Message, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if validate_non_neg_N_num(message.text):
        count = int(message.text)
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'count', count)
            await message.answer(f"Количество обновлено: {count}")
            await state.clear()
            return
        await state.update_data(count=message.text)
        await state.set_state(SeizureForm.triggers)
        await state.update_data(selected_triggers=[], current_page=0)
        await message.answer("Выберите или введите возможные триггеры: ", reply_markup=generate_features_keyboard([], 0, 5, action_btns=action_btns_flag))
    else:
        await message.answer("<u>Количество приступов должно быть любым не отрицательным числом\nНапример: 1 или 5</u>", parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb())

async def handle_toggle_trigger(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, feature, current_page = callback.data.split(':', 2)
    action_btns_flag = await get_action_btns_flag(state)
    data = await state.get_data()
    selected_triggers = data.get("selected_triggers", [])
    if feature in selected_triggers:
        selected_triggers.remove(feature)
    else:
        selected_triggers.append(feature)
    await state.update_data(selected_triggers=selected_triggers)
    await callback.message.edit_text('Выберите или введите возможные триггеры: ',
        reply_markup=generate_features_keyboard(selected_triggers, current_page, 5, action_btns=action_btns_flag)
    )
    await callback.answer()

async def handle_triggers_page(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    action_btns_flag = await get_action_btns_flag(state)
    selected_triggers = data.get("selected_triggers", [])
    print(callback.data)
    new_page = callback.data.split(':', 1)[1]

    await state.update_data(current_page=new_page)
    await callback.message.edit_text('Выберите или введите возможные триггеры: ',
        reply_markup=generate_features_keyboard(selected_triggers, int(new_page), 5, action_btns=action_btns_flag)
    )
    await callback.answer()

async def handle_save_toggled_triggers(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    selected_triggers = data.get("selected_triggers", [])
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await orm_update_seizure(db, int(seizure_id), int(profile_id), 'triggers', ",".join(selected_triggers))
        await callback.message.answer(f"Сохраненные триггеры обновлены: {'Список пуст' if len(selected_triggers) == 0 else ", ".join(selected_triggers)}")
        await callback.answer()
        await state.clear()
        return
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

async def handle_triggers_by_message(message: Message, state: FSMContext, db: AsyncSession):
    if validate_less_than_250(message.text):
        data = await state.get_data()
        triggers_list = data.get('selected_triggers')
        print(f'triggers list - {triggers_list}')
        triggers = ''
        if len(triggers_list) == 0:
            triggers = message.text
        else:
            triggers = ", ".join(triggers_list) + ", " + message.text

        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'triggers', triggers)
            await message.answer(f"Сохраненные триггеры обновлены: {'Список пуст' if triggers is None else triggers}")
            await state.clear()
            return
        await state.update_data(triggers=triggers)
        await state.set_state(SeizureForm.severity)
        await message.answer("Оцените степень тяжести приступа от 1 до 10: ", reply_markup=get_severity_kb())
    else:
        await message.answer("<u>Список не должен быть длиннее 250 символов</u>", parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb())


async def handle_severity(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    print(action_btns_flag)
    severity = callback.data.split(":")[1]
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == "edit":
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await orm_update_seizure(db, int(seizure_id), int(profile_id), 'severity', severity)
        await callback.message.answer(f"Тяжесть обновлена: {severity}")
        await callback.answer()
        await state.clear()
    else:
        await state.update_data(severity=severity)
        await callback.message.edit_text(f"Оставьте комментарий, если это нужно", reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))
        await state.set_state(SeizureForm.comment)
        await callback.answer()

#async def handle_duration_cb(callback: CallbackQuery, state: FSMContext, db: AsyncSession):

async def handle_duration_by_cb(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    duration_in_seconds = callback.data.split('-', 2)[1]
    action_btns_flag = await get_action_btns_flag(state)
    print(duration_in_seconds)
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await orm_update_seizure(db, int(seizure_id), int(profile_id), 'duration', int(duration_in_seconds))
        await callback.message.answer(f"Продолжительность обновлена: около {get_minutes_and_seconds(duration_in_seconds)}")
        await callback.answer()
        await state.clear()
        return
    await state.update_data(duration=duration_in_seconds)
    await callback.message.edit_text("Если в рамках одного припадка было несколько приступов, выберите их количество: ", reply_markup=get_count_of_seizures_kb(action_btns_flag))
    await state.set_state(SeizureForm.count)
    await callback.answer()


async def handle_duration_by_message(message: Message, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if validate_non_neg_N_num(message.text):
        duration = message.text
        duration = int(float(duration))
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'duration', duration * 60)
            await message.answer(f"Продолжительность обновлена: около {get_minutes_and_seconds(duration * 60)}")
            await state.clear()
        else:
            await state.update_data(duration=int(duration) * 60)
            await state.set_state(SeizureForm.count)
            await message.answer("Если в рамках одного припадка было несколько приступов, выберите их количество: ", reply_markup=get_count_of_seizures_kb(action_btns=action_btns_flag))
    else:
        await message.answer("Продолжительность приступа должна быть любым не отрицательным числом (в минутах)\nНапример: 0 или 3", parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))

async def handle_comment(message: Message, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if validate_less_than_250(message.text):
        comment = message.text
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'comment', comment)
            await message.answer(f"Комментарий обновлён: {comment}")
            await state.clear()
            return
        await state.update_data(comment=comment)
        await state.set_state(SeizureForm.video_tg_id)
        await message.answer("Пришлите видео приступа. Это может быть кружок или mp4 файл в любом виде: ", reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))
    else:
        await message.answer("<u>Комментарий не должен быть длиннее 250 символов</u>", parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))

async def handle_video(message: Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        if message.video:
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'video_tg_id', message.video.file_id)
            await message.answer("Видео сохранено")
        elif message.video_note:
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'video_tg_id', message.video_note.file_id)
            await message.answer("Видео сохранено")
        elif message.document.mime_type == 'video/mp4':
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'video_tg_id', message.document.file_id)
            await message.answer("Видео сохранено")
        else:
            await message.answer("Пришлите видео, кружок или mp4 документ.")
        await state.clear()
        return
    if message.video:
        await state.update_data(video_tg_id=message.video.file_id)
        await message.answer("Видео сохранено", reply_markup=get_temporary_cancel_submit_kb())
    elif message.video_note:
        await state.update_data(video_tg_id=message.video_note.file_id)
        await message.answer("Видео сохранено", reply_markup=get_temporary_cancel_submit_kb())
    elif message.document.mime_type == 'video/mp4':
        await state.update_data(video_tg_id=message.document.file_id)
        await message.answer("Видео сохранено", reply_markup=get_temporary_cancel_submit_kb())
    else:
        await message.answer("Пришлите видео, кружок или mp4 документ.")
    await state.set_state(SeizureForm.location)
    await message.answer("Напишите, где случился приступ или пришлите вашу геолокацию (нажмите на кнопку внизу): ", reply_markup=get_geolocation_for_timezone_kb())

async def handle_geolocation(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    latitude = message.location.latitude
    longitude = message.location.longitude
    location_coords = f"{latitude}|{longitude}"
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await orm_update_seizure(db, int(seizure_id), int(profile_id), 'location', location_coords)
        await message.answer(f"Геолокация обновлена: ", reply_markup=ReplyKeyboardRemove())
        await bot.send_location(chat_id=message.chat.id, latitude=latitude, longitude=longitude)
        await state.clear()
        return
    await state.update_data(location=location_coords)
    await message.answer("Геолокация сохранена.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Нажмите на кнопку 'Завершить'.", reply_markup=get_temporary_cancel_submit_kb())

async def handle_location_by_message(message: Message, state: FSMContext, db: AsyncSession):
    location = message.text
    if validate_less_than_250(location):
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'location', location)
            await message.answer(f"Место приступа сохранено: {location}")
            await state.clear()
        else:
            await state.update_data(location_by_message=location)
            await state.set_state(SeizureForm.count)
            await message.answer("Место приступа сохранено", reply_markup=ReplyKeyboardRemove())
            await message.answer("Все параметры заполнены, завершите или отмените заполнение: ", reply_markup=get_final_seizure_btns())
    else:
        await message.answer("Длина названия места не может превышать 250 символов", parse_mode='HTML')
