from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from services.graph_stat_builder import (
    get_year_gist, get_month_gist, get_total_seizure_count,
    get_day_without_seizures
)
analytics_router = Router()

@analytics_router.message(Command('graphs'))
async def process_graphs_cmd(message: Message, state: FSMContext, db: AsyncSession):
    await message.answer(
        f"Вывести график за год - /get_year_gist\n\n"
        f"Вывести график за месяц - /get_month_gist"
    )


@analytics_router.message(F.text == '/get_year_gist')
async def process_graphs_cmd(message: Message, state: FSMContext, db: AsyncSession):
    await get_year_gist(db, message)

@analytics_router.message(F.text == '/get_month_gist')
async def process_graphs_cmd(message: Message, state: FSMContext, db: AsyncSession):
    await get_month_gist(db, message)


@analytics_router.message(Command('stats'))
async def process_stats_cmd(message: Message, state: FSMContext, db: AsyncSession):
    total_count = await get_total_seizure_count(db, message)
    days_without_seizures = await get_day_without_seizures(db, message)
    await message.answer(
        f"Всего приступов: {total_count}\n"
        f"Дней без приступов: {days_without_seizures}"
    )