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
from database.redis_query import get_redis_cached_current_profile
from i18n import get_seizure_types, t
from services.notes_formatters import get_minutes_and_seconds
from services.redis_cache_data import get_cached_current_profile, get_cached_profile_triggers_list, get_cached_triggers_list
from services.validators import (
    validate_non_neg_N_num, validate_less_than_250, validate_date,
    validate_time,
)
from use_cases.seizures import update_seizure_field
from handlers_logic.states_factories import SeizureForm
from keyboards.seizure_kb import (
    generate_seizure_type_keyboard, get_year_date_kb, get_month_date_kb, get_day_kb,
    get_severity_kb, get_temporary_cancel_submit_kb, generate_features_keyboard,
    get_count_of_seizures_kb, get_duration_kb, get_time_ranges_kb, get_stop_duration_kb, get_final_seizure_btns
)
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb


async def _save_seizure_edit(
    db: AsyncSession,
    chat_id: int,
    seizure_id,
    profile_id,
    attribute: str,
    new_value,
) -> None:
    await update_seizure_field(
        db,
        user_id=chat_id,
        profile_id=int(profile_id),
        seizure_id=int(seizure_id),
        attribute=attribute,
        new_value=new_value,
    )


async def handle_skip_step(message: Message, state: FSMContext, db):
    current_state = await state.get_state()
    if (current_state is None) or (str(current_state).split(':', 1)[0] != "SeizureForm"):
        return await message.answer(t("seizure_form.restart"))
    if str(current_state).split(':', 1)[0] == "SeizureForm":
        await state.set_state(SeizureForm.next_state(current_state))
        if current_state == "SeizureForm:hour":
            await message.edit_text(t("seizure_form.select_duration"), reply_markup=get_duration_kb())
        elif current_state == "SeizureForm:duration":
            await message.edit_text(t("seizure_form.select_count"), reply_markup=get_count_of_seizures_kb())
        elif current_state == "SeizureForm:count":
            keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
            await message.answer(t("seizure_form.select_type"), reply_markup=keyboard)
        elif current_state == 'SeizureForm:type_of_seizure':
            print('ну и')
            current_profile = await get_cached_current_profile(db, message.chat.id)
            print('ну и2')
            global_triggers = await get_cached_triggers_list(db, message.chat.id)
            print('ну и3')
            profiles_triggers = await get_cached_profile_triggers_list(db, message.chat.id, int(current_profile.split('|', 1)[0]))
            print('ну и4')
            print(profiles_triggers + global_triggers)
            await message.edit_text(t("seizure_form.select_triggers"), reply_markup=generate_features_keyboard(profiles_triggers + global_triggers, [], 0, 5))
        elif current_state == "SeizureForm:triggers":
            await message.edit_text(t("seizure_form.select_severity"), reply_markup=get_severity_kb())
        elif current_state == "SeizureForm:severity":
            await message.edit_text(t("seizure_form.enter_comment"), reply_markup=get_temporary_cancel_submit_kb())
        elif current_state == "SeizureForm:comment":
            await message.edit_text(t("seizure_form.enter_video"), reply_markup=get_temporary_cancel_submit_kb())
        elif current_state == "SeizureForm:video_tg_id":
            await message.edit_text(t("seizure_form.enter_location"), reply_markup=get_temporary_cancel_submit_kb())
            await message.answer(t("seizure_form.enter_location_or_geo"), reply_markup=get_geolocation_for_timezone_kb())
        elif current_state == "SeizureForm:location":
            await message.answer(t("seizure_form.form_complete"), reply_markup=get_final_seizure_btns())

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

    await message.answer(t("seizure_form.stop_duration"), reply_markup=get_stop_duration_kb())

async def handle_stop_tracking_duration(message: Message, state: FSMContext):
    seizure_data = await state.get_data()
    duration_flag_str = seizure_data.get('exact_duration', None)
    print(duration_flag_str)
    if duration_flag_str is None:
        await message.answer(t("seizure_form.restart"))

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
    await message.edit_text(t("seizure_form.count_series"), reply_markup=get_count_of_seizures_kb())
    await message.answer(t("seizure_form.duration_recorded", duration=get_minutes_and_seconds(duration_diff)))
    await state.set_state(SeizureForm.count)

async def ask_for_a_year(message: Message, state: FSMContext):
    action_btns_flag = await get_action_btns_flag(state)
    await message.answer(t("seizure_form.select_year_or_date"),
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
            await _save_seizure_edit(db, callback.message.chat.id, seizure_id, profile_id, 'date', parsed["date"])
            await callback.message.answer(t("seizure_form.date_updated", value=parsed["date"]))
            await callback.answer()
            await state.clear()
            return
        else:
            await state.update_data(date_short=parsed["date"])
            await state.set_state(SeizureForm.hour)
            await callback.message.edit_text(
                t("seizure_form.enter_time"),
                reply_markup=get_time_ranges_kb(action_btns=action_btns_flag)
            )
            return
    await state.update_data(year=parsed["value"])
    await state.set_state(SeizureForm.month)
    await callback.message.edit_text(
        t("seizure_form.year_selected", year=parsed['value']),
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
        t("seizure_form.month_selected", month_name=month_name),
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
        await _save_seizure_edit(db, callback.message.chat.id, seizure_id, profile_id, 'date', new_date)
        await callback.message.answer(t("seizure_form.date_updated", value=new_date))
        await callback.answer()
        await state.clear()
    else:
        await state.update_data(day=format_small_date_numbers(day_index))
        await state.set_state(SeizureForm.hour)
        await callback.message.edit_text(
            t("seizure_form.enter_time_with_day", day=day_index),
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
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'date', date)
            await message.answer(t("seizure_form.date_updated", value=date))
            await state.clear()
        else:
            await state.update_data(date_short=date)
            await state.set_state(SeizureForm.hour)
            await message.answer(
                t("seizure_form.enter_time"),
                  reply_markup=get_time_ranges_kb(action_btns=action_btns_flag)
            )
    else:
        await message.answer(
            t("seizure_form.invalid_date"),
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
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'time', time)
            await message.answer(t("seizure_form.time_updated", value=time))
            await state.clear()
            return
        await state.update_data(time_of_day=time)
        print(message.text)
        await state.set_state(SeizureForm.duration)
        await message.answer(
            t("seizure_form.enter_duration_minutes"),
            reply_markup=get_duration_kb(action_btns=action_btns_flag)
        )
        # await state.set_state(SeizureForm.duration)
        # await message.answer(
        #     "Если в рамках одного приступа была серия приступов, выберите их количество",
        #     reply_markup=get_count_of_seizures_kb(action_btns=action_btns_flag))
    else:
        await message.answer(
            t("seizure_form.invalid_time"),
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
        await _save_seizure_edit(db, callback.message.chat.id, seizure_id, profile_id, 'time', time)
        await callback.message.answer(t("seizure_form.time_updated", value=time))
        await callback.answer()
        await state.clear()
        return
    await state.set_state(SeizureForm.duration)
    await callback.message.edit_text(
        t("seizure_form.enter_duration_minutes"),
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
        await _save_seizure_edit(db, callback.message.chat.id, seizure_id, profile_id, 'count', count_of_seizures)
        await callback.message.answer(t("seizure_form.count_updated", value=count_of_seizures))
        await callback.answer()
        await state.clear()
        return
    await state.update_data(count=count_of_seizures)
    await state.set_state(SeizureForm.type_of_seizure)
    keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
    await callback.message.edit_text(t("seizure_form.select_type"), reply_markup=keyboard)
    await callback.answer()

async def handle_count_by_message(message: Message, state: FSMContext, db: AsyncSession):
    if validate_non_neg_N_num(message.text):
        count = int(message.text)
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'count', count)
            await message.answer(t("seizure_form.count_updated", value=count))
            await state.clear()
            return
        await state.update_data(count=message.text)
        await state.set_state(SeizureForm.type_of_seizure)
        keyboard = generate_seizure_type_keyboard(current_page=0, page_size=6)
        await message.answer(t("seizure_form.select_type"), reply_markup=keyboard)
    else:
        await message.answer(t("seizure_form.invalid_count"), parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb())

async def handle_type_of_seizure_page(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, current_page = callback.data.split(':', 1)
    print(current_page)
    keyboard = generate_seizure_type_keyboard(current_page=current_page, page_size=6)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()

async def handle_type_of_seizure_save(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    type_of_seizure_id = callback.data.split(':', 1)[1]
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        seizure_type = get_seizure_types()[int(type_of_seizure_id)]
        await _save_seizure_edit(db, callback.message.chat.id, seizure_id, profile_id, 'type_of_seizure', seizure_type)
        await callback.message.answer(t("seizure.type_updated", seizure_type=seizure_type))
        await state.clear()
        return
    print(type_of_seizure_id)
    await state.update_data(type_of_seizure=get_seizure_types()[int(type_of_seizure_id)])

    await state.set_state(SeizureForm.triggers)
    await state.update_data(selected_triggers=[], current_page=0)
    current_profile = await get_cached_current_profile(db, callback.message.chat.id)
    global_triggers = await get_cached_triggers_list(db, callback.message.chat.id)
    profiles_triggers = await get_cached_profile_triggers_list(db, callback.message.chat.id, int(current_profile.split('|', 1)[0]))
    print(profiles_triggers+global_triggers)
    await callback.message.edit_text(t("seizure_form.select_triggers"), reply_markup=generate_features_keyboard(
        profiles_triggers+global_triggers,
        [],
        0,
        5,
        action_btns=action_btns_flag)
        )
    await callback.answer()

async def handle_toggle_trigger(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, feature, current_page = callback.data.split(':', 2)
    action_btns_flag = await get_action_btns_flag(state)
    data = await state.get_data()
    selected_triggers = data.get("selected_triggers", [])
    if feature in selected_triggers:
        selected_triggers.remove(feature)
    else:
        selected_triggers.append(feature)
    current_profile = await get_cached_current_profile(db, callback.message.chat.id)
    global_triggers = await get_cached_triggers_list(db, callback.message.chat.id)
    profiles_triggers = await get_cached_profile_triggers_list(db, callback.message.chat.id, int(current_profile.split('|', 1)[0]))
    await state.update_data(selected_triggers=selected_triggers)
    await callback.message.edit_text(t("seizure_form.select_triggers"),
        reply_markup=generate_features_keyboard(
            profiles_triggers+global_triggers,
            selected_triggers,
            current_page,
            5,
            action_btns=action_btns_flag
            )
    )
    await callback.answer()

async def handle_triggers_page(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    action_btns_flag = await get_action_btns_flag(state)
    selected_triggers = data.get("selected_triggers", [])
    new_page = callback.data.split(':', 1)[1]
    current_profile = await get_cached_current_profile(db, callback.message.chat.id)
    global_triggers = await get_cached_triggers_list(db, callback.message.chat.id)
    profiles_triggers = await get_cached_profile_triggers_list(db, callback.message.chat.id, int(current_profile.split('|', 1)[0]))
    await state.update_data(current_page=new_page)
    await callback.message.edit_text(t("seizure_form.select_triggers"),
        reply_markup=generate_features_keyboard(
            features_list=profiles_triggers + global_triggers,
            selected_features=selected_triggers,
            current_page=int(new_page),
            page_size=5,
            action_btns=action_btns_flag
            )
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
        await _save_seizure_edit(db, callback.message.chat.id, seizure_id, profile_id, 'triggers', ",".join(selected_triggers))
        triggers_value = (
            t("seizure_form.triggers_empty")
            if len(selected_triggers) == 0
            else ", ".join(selected_triggers)
        )
        await callback.message.answer(t("seizure_form.triggers_updated", value=triggers_value))
        await callback.answer()
        await state.clear()
        return
    if selected_triggers:
        await state.set_state(SeizureForm.severity)
        print(selected_triggers)
        await callback.message.edit_text(t("seizure_form.select_severity"), reply_markup=get_severity_kb())
    else:
        await state.update_data(selected_triggers=[])
        await state.set_state(SeizureForm.severity)
        print(selected_triggers)
        await callback.message.edit_text(t("seizure_form.select_severity"), reply_markup=get_severity_kb())
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
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'triggers', triggers)
            triggers_value = t("seizure_form.triggers_empty") if triggers is None else triggers
            await message.answer(t("seizure_form.triggers_updated", value=triggers_value))
            await state.clear()
            return
        await state.update_data(triggers=triggers)
        await state.set_state(SeizureForm.severity)
        await message.answer(t("seizure_form.select_severity"), reply_markup=get_severity_kb())
    else:
        await message.answer(t("seizure_form.triggers_too_long"), parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb())


async def handle_severity(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    print(action_btns_flag)
    severity = callback.data.split(":")[1]
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == "edit":
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await _save_seizure_edit(db, callback.message.chat.id, seizure_id, profile_id, 'severity', severity)
        await callback.message.answer(t("seizure_form.severity_updated", severity=severity))
        await callback.answer()
        await state.clear()
    else:
        await state.update_data(severity=severity)
        await callback.message.edit_text(t("seizure_form.enter_comment"), reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))
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
        await _save_seizure_edit(db, callback.message.chat.id, seizure_id, profile_id, 'duration', int(duration_in_seconds))
        await callback.message.answer(t("seizure_form.duration_updated", duration=get_minutes_and_seconds(duration_in_seconds)))
        await callback.answer()
        await state.clear()
        return
    await state.update_data(duration=duration_in_seconds)
    await callback.message.edit_text(t("seizure_form.select_count"), reply_markup=get_count_of_seizures_kb(action_btns_flag))
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
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'duration', duration * 60)
            await message.answer(t("seizure_form.duration_updated", duration=get_minutes_and_seconds(duration * 60)))
            await state.clear()
        else:
            await state.update_data(duration=int(duration) * 60)
            await state.set_state(SeizureForm.count)
            await message.answer(t("seizure_form.select_count"), reply_markup=get_count_of_seizures_kb(action_btns=action_btns_flag))
    else:
        await message.answer(t("seizure_form.invalid_duration"), parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))

async def handle_comment(message: Message, state: FSMContext, db: AsyncSession):
    action_btns_flag = await get_action_btns_flag(state)
    if validate_less_than_250(message.text):
        comment = message.text
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'comment', comment)
            await message.answer(t("seizure_form.comment_updated", comment=comment))
            await state.clear()
            return
        await state.update_data(comment=comment)
        await state.set_state(SeizureForm.video_tg_id)
        await message.answer(t("seizure_form.enter_video"), reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))
    else:
        await message.answer(t("seizure_form.comment_too_long"), parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb(action_btns=action_btns_flag))

async def handle_video(message: Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        if message.video:
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'video_tg_id', message.video.file_id)
            await message.answer(t("seizure_form.video_saved"))
        elif message.video_note:
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'video_tg_id', message.video_note.file_id)
            await message.answer(t("seizure_form.video_saved"))
        elif message.document.mime_type == 'video/mp4':
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'video_tg_id', message.document.file_id)
            await message.answer(t("seizure_form.video_saved"))
        else:
            await message.answer(t("seizure_form.video_invalid"))
        await state.clear()
        return
    if message.video:
        await state.update_data(video_tg_id=message.video.file_id)
        await message.answer(t("seizure_form.video_saved"), reply_markup=get_temporary_cancel_submit_kb())
    elif message.video_note:
        await state.update_data(video_tg_id=message.video_note.file_id)
        await message.answer(t("seizure_form.video_saved"), reply_markup=get_temporary_cancel_submit_kb())
    elif message.document.mime_type == 'video/mp4':
        await state.update_data(video_tg_id=message.document.file_id)
        await message.answer(t("seizure_form.video_saved"), reply_markup=get_temporary_cancel_submit_kb())
    else:
        await message.answer(t("seizure_form.video_invalid"))
    await state.set_state(SeizureForm.location)
    await message.answer(t("seizure_form.location_prompt"), reply_markup=get_geolocation_for_timezone_kb())

async def handle_geolocation(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    latitude = message.location.latitude
    longitude = message.location.longitude
    location_coords = f"{latitude}|{longitude}"
    data = await state.get_data()
    mode = data.get("mode", "create")
    if mode == 'edit':
        seizure_id = data["seizure_id"]
        profile_id = data["profile_id"]
        await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'location', location_coords)
        await message.answer(t("seizure_form.geolocation_updated"), reply_markup=ReplyKeyboardRemove())
        await bot.send_location(chat_id=message.chat.id, latitude=latitude, longitude=longitude)
        await state.clear()
        return
    await state.update_data(location=location_coords)
    await message.answer(t("seizure_form.geolocation_saved"), reply_markup=ReplyKeyboardRemove())
    await message.answer(t("seizure_form.finish_prompt"), reply_markup=get_temporary_cancel_submit_kb())

async def handle_location_by_message(message: Message, state: FSMContext, db: AsyncSession):
    location = message.text
    if validate_less_than_250(location):
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await _save_seizure_edit(db, message.chat.id, seizure_id, profile_id, 'location', location)
            await message.answer(t("seizure_form.location_saved", location=location))
            await state.clear()
        else:
            await state.update_data(location_by_message=location)
            await state.set_state(SeizureForm.count)
            await message.answer(t("seizure_form.location_saved_short"), reply_markup=ReplyKeyboardRemove())
            await message.answer(t("seizure_form.form_complete"), reply_markup=get_final_seizure_btns())
    else:
        await message.answer(t("seizure_form.location_too_long"), parse_mode='HTML')
