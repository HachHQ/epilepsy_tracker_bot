import os
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.delivery import send_chart_photo
from filters.correct_commands import ProfileIsSetCb, ProfileIsSetMsg
from i18n import t
from keyboards.journal_kb import get_graphs_type
from keyboards.seizure_kb import build_statistics_navigation_keyboard
from services.graph_stat_builder import (
    ChartBuildResult,
    draw_avg_duration_bar_chart,
    format_seizure_statistics,
    format_top_features,
    render_efficiency_gist,
    render_hour_distribution,
    render_month_distribution,
    render_month_gist,
    render_weekday_distribution,
    render_year_gist,
)
from services.profile_ref import ProfileRef
from use_cases import analytics as analytics_use_cases

analytics_router = Router()


def _year_lines(prefix: str, template_key: str) -> str:
    current_year = datetime.now(UTC).year
    lines = []
    for year in (current_year, current_year - 1, current_year - 2):
        lines.append(t(template_key, year=year) + "\n\n")
    return "".join(lines)


async def _deliver_chart(message: Message, result: ChartBuildResult) -> None:
    if result.error or not result.image_path or result.caption is None:
        await message.answer(result.error or t("common.generic_error"))
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
async def switch_to_features(
    callback: CallbackQuery, db: AsyncSession, current_profile: ProfileRef | None
):
    profile = current_profile
    if not profile:
        return await callback.message.edit_text(t("analytics.select_profile_first"))

    result = await analytics_use_cases.get_profile_feature_stats(db, profile.id)
    text = format_top_features(profile.name, result["top_symptoms"], result["top_triggers"], result["top_types"])
    await callback.message.edit_text(
        text,
        reply_markup=build_statistics_navigation_keyboard(current_page="features"),
        parse_mode="HTML",
    )
    await callback.answer()


@analytics_router.message(F.text.startswith("/get_hour_distribution"), ProfileIsSetMsg())
async def handle_hour_distribution(
    message: Message, db: AsyncSession, current_profile: ProfileRef | None
):
    series = await analytics_use_cases.build_hour_distribution(db, current_profile)
    await _deliver_chart(message, render_hour_distribution(series))


@analytics_router.message(F.text == "/get_week_distribution", ProfileIsSetMsg())
async def handle_weekday_distribution(
    message: Message, db: AsyncSession, current_profile: ProfileRef | None
):
    series = await analytics_use_cases.build_weekday_distribution(db, current_profile)
    await _deliver_chart(message, render_weekday_distribution(series))


@analytics_router.message(F.text == "/get_month_distribution", ProfileIsSetMsg())
async def handle_month_distribution(
    message: Message, db: AsyncSession, current_profile: ProfileRef | None
):
    series = await analytics_use_cases.build_calendar_month_distribution(db, current_profile)
    await _deliver_chart(message, render_month_distribution(series))


@analytics_router.message(F.text.regexp(r"/get_duration_(\d{4})"), ProfileIsSetMsg())
async def get_duration_graph(
    message: Message, db: AsyncSession, current_profile: ProfileRef | None
):
    year = int(message.text.split("_")[-1])
    profile = current_profile
    if profile is None:
        return await message.answer(t("analytics.select_profile"))
    profile_id = profile.id
    profile_name = profile.name
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
async def handle_drug_efficiency_command(
    message: Message, db: AsyncSession, current_profile: ProfileRef | None
):
    await _deliver_chart(
        message,
        render_efficiency_gist(
            await analytics_use_cases.build_efficiency_series(db, current_profile, message.text)
        ),
    )


@analytics_router.message(F.text == '/get_year_gist', ProfileIsSetMsg())
async def process_year_gist(
    message: Message, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    await _deliver_chart(
        message, render_year_gist(await analytics_use_cases.build_year_counts(db, current_profile))
    )


@analytics_router.message(F.text == '/get_month_gist', ProfileIsSetMsg())
async def process_month_gist(
    message: Message, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    await _deliver_chart(
        message, render_month_gist(await analytics_use_cases.build_month_counts(db, current_profile))
    )


@analytics_router.callback_query((F.data == "stats") | (F.data == 'stats_edit'), ProfileIsSetCb())
async def process_stats_cmd(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    stat_data = await analytics_use_cases.build_seizure_statistics(
        db, current_profile, callback.message.chat.id
    )
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
