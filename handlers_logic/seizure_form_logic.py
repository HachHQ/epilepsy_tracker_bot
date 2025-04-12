from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from services.validators import validate_count_of_seizures, validate_triggers_list, validate_date
from database.orm_query import orm_update_seizure
from handlers_logic.states_factories import SeizureForm
from keyboards.seizure_kb import (get_year_date_kb, get_month_date_kb, get_day_kb,
                                 get_severity_kb, get_temporary_cancel_submit_kb, generate_features_keyboard,
                                 get_count_of_seizures_kb, get_duration_kb)

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

async def ask_for_a_year(message: Message):
    await message.answer(f"Выберите год или сразу день из преложенных\n\n<u>Либо введите дату вручную в формате ГОД-МЕСЯЦ-ДЕНЬ</u>",
                                reply_markup=get_year_date_kb(3,1),
                                parse_mode='HTML')

async def handle_short_date(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    parsed = parse_callback_data(callback.data)

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
                reply_markup=get_temporary_cancel_submit_kb()
            )
            return
    await state.update_data(year=parsed["value"])
    await state.set_state(SeizureForm.month)
    await callback.message.edit_text(
        f"Выбран {parsed['value']} год.\nВыберите месяц:",
        reply_markup=get_month_date_kb()
    )

async def handle_day(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    day_index = callback.data.split(':', 1)[1]
    data = await state.get_data()
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
        await callback.message.edit_text(f"Выбрано число: {day_index}\n\nВведите примерное время в которое произошел приступ в формате ЧАС:МИНУТЫ", reply_markup=get_temporary_cancel_submit_kb())

async def handle_date_by_message(message: Message, state: FSMContext, db: AsyncSession):
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
            await message.answer("Введите примерное время в которое произошел приступ в формате ЧАС:МИНУТЫ", reply_markup=get_temporary_cancel_submit_kb())
    else:
        await message.answer("<u>Введите дату в формате ГОД-МЕСЯЦ-ДЕНЬ\nНапример: 2020-02-01</u>", parse_mode="HTML", reply_markup=get_temporary_cancel_submit_kb())


async def handle_severity(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
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
        await callback.message.edit_text(f"Введите примерную продолжительность в минутах: ", reply_markup=get_temporary_cancel_submit_kb())
        await state.set_state(SeizureForm.duration)
        await callback.answer()

async def handle_duration(message: Message, state: FSMContext, db: AsyncSession):
    if validate_count_of_seizures(message.text):
        duration = message.text
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'duration', int(duration))
            await message.answer(f"Продолжительность обновлена: {duration}")
            await state.clear()
        else:
            await state.update_data(duration=duration)
            await state.set_state(SeizureForm.comment)
            await message.answer("Введите любой комментарий к приступу: ", reply_markup=get_temporary_cancel_submit_kb())
    else:
        await message.answer("Продолжительность приступа должна быть любым не отрицательным числом (в минутах)\nНапример: 0 или 55</u>", parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb())

async def handle_comment(message: Message, state: FSMContext, db: AsyncSession):
    if validate_triggers_list(message.text):
        comment = message.text
        data = await state.get_data()
        mode = data.get("mode", "create")
        if mode == 'edit':
            seizure_id = data["seizure_id"]
            profile_id = data["profile_id"]
            await orm_update_seizure(db, int(seizure_id), int(profile_id), 'comment', comment)
            await message.answer(f"Комментарий обновлён: {comment}")
            await state.clear()
        await state.update_data(comment=comment)
        await state.set_state(SeizureForm.video_tg_id)
        await message.answer("Пришлите видео приступа: ", reply_markup=get_temporary_cancel_submit_kb())
    else:
        await message.answer("<u>Комментарий не должен быть длиннее 250 символов</u>", parse_mode='HTML', reply_markup=get_temporary_cancel_submit_kb())
