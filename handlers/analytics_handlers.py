from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from filters.correct_commands import ProfileIsSetCb, ProfileIsSetMsg
from services.graph_stat_builder import (
    get_year_gist, get_month_gist, get_total_seizure_count,
    get_day_without_seizures, get_min_max_duration_of_seizure, get_avg_duration_of_seizure,
    get_avg_duration_of_seizure_in_a_month, get_avg_duration_of_seizure_in_a_week, get_avg_days_without_seizures
)
from services.redis_cache_data import get_user_local_datetime
analytics_router = Router()

@analytics_router.callback_query(F.data == "graphs", ProfileIsSetCb())
async def process_graphs_cmd(callback: CallbackQuery):
    await callback.message.answer(
        f"Вывести график за год - /get_year_gist\n\n"
        f"Вывести график за месяц - /get_month_gist"
    )
    await callback.answer()


@analytics_router.message(F.text == '/get_year_gist', ProfileIsSetMsg())
async def process_graphs_cmd(message: Message, state: FSMContext, db: AsyncSession):
    await get_year_gist(db, message)

@analytics_router.message(F.text == '/get_month_gist', ProfileIsSetMsg())
async def process_graphs_cmd(message: Message, state: FSMContext, db: AsyncSession):
    await get_month_gist(db, message)


@analytics_router.callback_query(F.data == "stats", ProfileIsSetCb())
async def process_stats_cmd(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    total_count = await get_total_seizure_count(db, callback.message)
    days_without_seizures = await get_day_without_seizures(db, callback.message)
    avg_days_without_seizures = await get_avg_days_without_seizures(db, callback.message)
    min_max_dur = await get_min_max_duration_of_seizure(db, callback.message)
    min_duration = min_max_dur.split('|', 1)[0] if min_max_dur is not None else None
    max_duration = min_max_dur.split('|', 1)[1] if min_max_dur is not None else None
    total_avg_duration = await get_avg_duration_of_seizure(db, callback.message)
    avg_duration_week = await get_avg_duration_of_seizure_in_a_week(db, callback.message)
    avg_duration_month = await get_avg_duration_of_seizure_in_a_month(db, callback.message)
    print("Локальное время", await get_user_local_datetime(db, callback.message.chat.id))
    await callback.message.answer(
        f"Всего приступов: {total_count}\n\n"
        f"Дней без приступов: {days_without_seizures}\n\n"
        f"Дней без приступов в среднем: {avg_days_without_seizures}\n\n"
        f"Средняя продолжительность: {total_avg_duration}\n\n"
        f"Минимальная и максимальная продолжительность:\n"
        f"{min_duration} | {max_duration}\n\n"
        f"Средняя продолжительность\n"
        f"за последнюю неделю: {avg_duration_week}\n"
        f"за последний месяц: {avg_duration_month}\n\n"
    )
    await callback.answer()