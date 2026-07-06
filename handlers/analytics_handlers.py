import os

from aiogram import Router, F
from aiogram.types import FSInputFile, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from adapters.telegram.delivery import send_chart_photo
from use_cases import analytics as analytics_use_cases
from filters.correct_commands import ProfileIsSetCb, ProfileIsSetMsg
from keyboards.journal_kb import get_graphs_type
from keyboards.seizure_kb import build_statistics_navigation_keyboard
from i18n import t
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


def _year_lines(prefix: str, template_key: str) -> str:
    current_year = datetime.now(timezone.utc).year
    lines = []
    for year in (current_year, current_year - 1, current_year - 2):
        lines.append(t(template_key, year=year) + "\n\n")
    return "".join(lines)


async def _deliver_chart(message: Message, result: ChartBuildResult) -> None:
    if result.error:
        await message.answer(result.error)
        return
    await send_chart_photo(message, result.image_path, result.caption)


@analytics_router.callback_query(F.data == "graphs", ProfileIsSetCb())
async def process_graphs_cmd(callback: CallbackQuery):
    await callback.message.edit_text(
        t("analytics.choose_graph_type"),
        reply_markup=get_graphs_type(),
    )
    await callback.answer()


@analytics_router.callback_query(F.data == "duration_graphs", ProfileIsSetCb())
async def process_duration_graphs(callback: CallbackQuery):
    await callback.message.answer(
        t("analytics.duration_graphs_intro") + "\n\n" + _year_lines("get_duration", "analytics.duration_year_line"),
    )
    await callback.answer()


@analytics_router.callback_query(F.data == "frequency_graphs", ProfileIsSetCb())
async def process_frequency_graphs(callback: CallbackQuery):
    await callback.message.answer(t("analytics.frequency_graphs_intro"))
    await callback.answer()


@analytics_router.callback_query(F.data == "efficiency_graphs", ProfileIsSetCb())
async def process_efficiency_graphs(callback: CallbackQuery, db: AsyncSession):
    await callback.message.answer(
        t("analytics.efficiency_graphs_intro") + "\n"
        + _year_lines("get_drug_efficiency", "analytics.efficiency_year_line"),
    )
    await callback.answer()


@analytics_router.callback_query(F.data == "view:features", ProfileIsSetCb())
async def switch_to_features(callback: CallbackQuery, db: AsyncSession):
    profile = await get_cached_current_profile(db, callback.message.chat.id)
    if not profile:
        return await callback.message.edit_text(t("analytics.select_profile_first"))

    profile_id = int(profile.split("|")[0])
    profile_name = profile.split("|")[1]

    result = await analytics_use_cases.get_profile_feature_stats(db, profile_id)
    text = format_top_features(profile_name, result["top_symptoms"], result["top_triggers"], result["top_types"])
    await callback.message.edit_text(
        text,
        reply_markup=build_statistics_navigation_keyboard(current_page="features"),
        parse_mode="HTML",
    )
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
    data = await analytics_use_cases.get_monthly_avg_duration(db, profile_id, year)
    if not data:
        return await message.answer(t("analytics.no_duration_data", year=year))
    chart_file = draw_avg_duration_bar_chart(data, year, profile_name)
    try:
        await message.answer_photo(
            photo=FSInputFile(chart_file),
            caption=t("analytics.duration_chart_caption", year=year, profile_name=profile_name),
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
async def process_year_gist(message: Message, state: FSMContext, db: AsyncSession):
    await _deliver_chart(message, await get_year_gist(db, message.chat.id))


@analytics_router.message(F.text == '/get_month_gist', ProfileIsSetMsg())
async def process_month_gist(message: Message, state: FSMContext, db: AsyncSession):
    await _deliver_chart(message, await get_month_gist(db, message.chat.id))


@analytics_router.callback_query((F.data == "stats") | (F.data == 'stats_edit'), ProfileIsSetCb())
async def process_stats_cmd(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    stat_data = await compute_seizure_statistics(db, callback.message.chat.id)
    if stat_data.get("error"):
        await callback.message.answer(stat_data["error"])
        await callback.answer()
        return
    text = format_seizure_statistics(stat_data)
    if callback.data == 'stats_edit':
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=build_statistics_navigation_keyboard(current_page="stats"),
        )
    else:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=build_statistics_navigation_keyboard(current_page="stats"),
        )
    await callback.answer()
