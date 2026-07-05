import os

from aiogram import Router, F
from aiogram.types import FSInputFile, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from adapters.telegram.delivery import send_chart_photo
from database.orm_query import get_avg_duration_by_month, get_top_seizure_features
from filters.correct_commands import ProfileIsSetCb, ProfileIsSetMsg
from keyboards.journal_kb import get_graphs_type
from keyboards.seizure_kb import build_statistics_navigation_keyboard
from services.graph_stat_builder import (
    ChartBuildResult,
    compute_seizure_statistics,
    draw_avg_duration_bar_chart,
    format_seizure_statistics,
    format_top_features,
    get_hour_distribution_plot,
    get_month_distribution_plot,
    get_weekday_distribution_plot,
    get_year_gist,
    get_month_gist,
    get_year_gist_with_courses,
)
from services.redis_cache_data import get_cached_current_profile

analytics_router = Router()


async def _deliver_chart(message: Message, result: ChartBuildResult) -> None:
    if result.error:
        await message.answer(result.error)
        return
    await send_chart_photo(message, result.image_path, result.caption)


@analytics_router.callback_query(F.data == "graphs", ProfileIsSetCb())
async def process_graphs_cmd(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите интересующий вас тип графиков:\n"
        f" - Продолжительность приступов \n"
        f" - Частота приступов\n"
        f" - Эффективность лекарств\n",
        reply_markup=get_graphs_type()
    )
    await callback.answer()

@analytics_router.callback_query(F.data == "duration_graphs", ProfileIsSetCb())
async def process_graphs_cmd(callback: CallbackQuery):
    await callback.message.answer(
        "Средняя продолжительность приступов по годам (вы можете построить график по интересующему вас году, добавив его в конец команды).\n\n"
        f"   - За {datetime.now(timezone.utc).year} год /get_duration_{datetime.now(timezone.utc).year}\n\n"
        f"   - За {datetime.now(timezone.utc).year - 1} год /get_duration_{datetime.now(timezone.utc).year - 1}\n\n"
        f"   - За {datetime.now(timezone.utc).year - 2} год /get_duration_{datetime.now(timezone.utc).year - 2}\n\n"
    )
    await callback.answer()

@analytics_router.callback_query(F.data == "frequency_graphs", ProfileIsSetCb())
async def process_graphs_cmd(callback: CallbackQuery):
    await callback.message.answer(
        "Распределение частоты приступов.\n"
        "   - В течение дня - /get_hour_distribution\n\n"
        "   - В течение недели - /get_week_distribution\n\n"
        "   - В течение года - /get_month_distribution\n\n"
        "Частота приступов по году/месяцу (вы можете построить график по интересующему вас году/месяцу, добавив его в конец команды).\n"
    )
    await callback.answer()

@analytics_router.callback_query(F.data == "efficiency_graphs", ProfileIsSetCb())
async def process_graphs_cmd(callback: CallbackQuery, db: AsyncSession):
    await callback.message.answer(
        "Частота приступов в контексте курсов лекарств: (вы можете построить график по интересующему вас году, добавив его в конец команды)\n"
        f"   - За {datetime.now(timezone.utc).year} год /get_drug_efficiency_{datetime.now(timezone.utc).year}\n\n"
        f"   - За {datetime.now(timezone.utc).year - 1} год /get_drug_efficiency_{datetime.now(timezone.utc).year - 1}\n\n"
        f"   - За {datetime.now(timezone.utc).year - 2} год /get_drug_efficiency_{datetime.now(timezone.utc).year - 2}\n\n"
    )
    await callback.answer()

@analytics_router.callback_query(F.data == "view:features", ProfileIsSetCb())
async def switch_to_features(callback: CallbackQuery, db: AsyncSession):
    profile = await get_cached_current_profile(db, callback.message.chat.id)
    if not profile:
        return await callback.message.edit_text("Сначала выберите профиль.")

    profile_id = int(profile.split("|")[0])
    profile_name = profile.split("|")[1]

    result = await get_top_seizure_features(db, profile_id)
    text = format_top_features(profile_name, result["top_symptoms"], result["top_triggers"], result["top_types"])
    await callback.message.edit_text(text, reply_markup=build_statistics_navigation_keyboard(current_page="features"), parse_mode="HTML")
    await callback.answer()

@analytics_router.message(F.text.startswith("/get_hour_distribution"), ProfileIsSetMsg())
async def handle_hour_distribution(message: Message, db: AsyncSession):
    await _deliver_chart(message, await get_hour_distribution_plot(db, message.chat.id))

@analytics_router.message(F.text == "/get_week_distribution", ProfileIsSetMsg())
async def handle_weekday_distribution(message: Message, db: AsyncSession):
    await _deliver_chart(message, await get_weekday_distribution_plot(db, message.chat.id))

@analytics_router.message(F.text == "/get_month_distribution", ProfileIsSetMsg())
async def handle_month_distribution(message: Message, db: AsyncSession):
    await _deliver_chart(message, await get_month_distribution_plot(db, message.chat.id))

@analytics_router.message(F.text.regexp(r"/get_duration_(\d{4})"), ProfileIsSetMsg())
async def get_duration_graph(message: Message, db: AsyncSession):
    year = int(message.text.split("_")[-1])
    profile = await get_cached_current_profile(db, message.chat.id)
    profile_id = int(profile.split("|")[0])
    profile_name = profile.split("|")[1]
    data = await get_avg_duration_by_month(db, profile_id, year)
    if not data:
        return await message.answer(f"Нет данных о продолжительности приступов за {year} год.")
    chart_file = draw_avg_duration_bar_chart(data, year, profile_name)
    try:
        await message.answer_photo(
            photo=FSInputFile(chart_file),
            caption=f"📊 Средняя продолжительность приступов по месяцам за {year} год для профиля <b>{profile_name}</b>",
            parse_mode="HTML",
        )
    finally:
        if os.path.exists(chart_file):
            os.remove(chart_file)

@analytics_router.message(F.text.startswith("/get_drug_efficiency_"), ProfileIsSetMsg())
async def handle_drug_efficiency_command(message: Message, db: AsyncSession):
    await _deliver_chart(
        message,
        await get_year_gist_with_courses(db, message.chat.id, message.text),
    )


@analytics_router.message(F.text == '/get_year_gist', ProfileIsSetMsg())
async def process_graphs_cmd(message: Message, state: FSMContext, db: AsyncSession):
    await _deliver_chart(message, await get_year_gist(db, message.chat.id))

@analytics_router.message(F.text == '/get_month_gist', ProfileIsSetMsg())
async def process_graphs_cmd(message: Message, state: FSMContext, db: AsyncSession):
    await _deliver_chart(message, await get_month_gist(db, message.chat.id))


@analytics_router.callback_query((F.data == "stats") | (F.data == 'stats_edit'), ProfileIsSetCb())
async def process_stats_cmd(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    stat_data = await compute_seizure_statistics(db, callback.message.chat.id)
    if stat_data.get("error"):
        await callback.message.answer(stat_data["error"])
        await callback.answer()
        return
    text = format_seizure_statistics(stat_data)
    if callback.data ==  'stats_edit':
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=build_statistics_navigation_keyboard(current_page="stats"))
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=build_statistics_navigation_keyboard(current_page="stats"))
    await callback.answer()
