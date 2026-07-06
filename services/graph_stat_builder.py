from dataclasses import dataclass

import os
from uuid import uuid4
import pandas as pd
import matplotlib.pyplot as plt
import calendar
import numpy as np
from scipy import stats
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from datetime import datetime, timezone, timedelta, date
from matplotlib import rcParams
from matplotlib.ticker import MaxNLocator

from database.models import MedicationCourse, Seizure

Path("temp_images").mkdir(exist_ok=True)

from i18n import get_month_abbreviations, get_weekday_abbreviations, t
from services.notes_formatters import get_minutes_and_seconds
from database.orm_query import (
from database.repositories.medications import list_profile_medications
    orm_get_seizures_by_profile_ascending,
    orm_get_seizures_for_a_specific_period,
    orm_get_seizures_for_a_specific_year,
)
from services.redis_cache_data import (
    get_cached_current_profile,
    get_user_local_datetime
)

MONTHS_RU = get_month_abbreviations()
WEEKDAYS_RU = get_weekday_abbreviations()


def _refresh_chart_labels() -> None:
    global MONTHS_RU, WEEKDAYS_RU
    MONTHS_RU = get_month_abbreviations()
    WEEKDAYS_RU = get_weekday_abbreviations()


@dataclass(frozen=True)
class ChartBuildResult:
    image_path: str | None = None
    caption: str | None = None
    error: str | None = None


def get_current_utc_context() -> tuple[datetime, int, int, str]:
    _refresh_chart_labels()
    current_date = datetime.now(timezone.utc)
    current_year = current_date.year
    current_month = current_date.month
    return current_date, current_year, current_month, MONTHS_RU[current_month - 1]

#GRAPHS
def make_a_gist(
        title,
        label_x,
        label_y,
        dataX,
        dataY,
        xticks
    ):
    rcParams['font.family'] = 'Lato'
    plt.figure(figsize=(10,6))
    plt.xlabel(label_x, fontproperties='Lato', fontsize=14)
    plt.ylabel(label_y, fontproperties='Lato', fontsize=14)
    plt.title(title, fontproperties='Lato', fontsize=18)
    plt.xticks(ticks=dataX, labels=xticks, fontsize=10)
    plt.grid(visible=True, which='both', linestyle='--', linewidth=0.5)
    return plt.bar(dataX, dataY)

async def get_year_gist(session: AsyncSession, chat_id: int) -> ChartBuildResult:
    _, current_year, _, _ = get_current_utc_context()
    current_profile = await get_cached_current_profile(session, chat_id)
    if current_profile is None:
        return ChartBuildResult(error=t("analytics.select_profile"))
    seizure_data = await orm_get_seizures_for_a_specific_period(
        session,
        int(current_profile.split('|', 1)[0]),
        current_year,
    )
    if len(seizure_data) == 0:
        return ChartBuildResult(error=t("analytics.no_chart_data"))
    month_arr = range(1, 13)
    count_seizures_by_month = [0] * 12
    for seizure in seizure_data:
        date = datetime.strptime(seizure.date, "%Y-%m-%d")
        if date.month in month_arr:
            count_seizures_by_month[date.month - 1] += 1
    make_a_gist(
        title=t("analytics.chart_seizures_by_month_year", year=current_year),
        label_x=t("analytics.chart_axis_month"),
        label_y=t("analytics.chart_axis_seizure_count"),
        dataX=month_arr,
        dataY=count_seizures_by_month,
        xticks=MONTHS_RU,
    )
    path = "temp_images/gist_year.png"
    plt.savefig(path)
    plt.close()
    return ChartBuildResult(
        image_path=path,
        caption=t(
            "analytics.caption_year_gist",
            year=current_year,
            profile_name=current_profile.split('|', 1)[1],
        ),
    )

async def get_month_gist(session: AsyncSession, chat_id: int) -> ChartBuildResult:
    current_date, current_year, current_month, current_month_in_russian = get_current_utc_context()
    days_range = calendar.monthrange(current_year, current_month)[1]
    days_range = [day for day in range(1, days_range + 1)]
    count_seizures_by_days = [0] * len(days_range)
    current_profile = await get_cached_current_profile(session, chat_id)
    if current_profile is None:
        return ChartBuildResult(error=t("analytics.select_profile"))
    seizures_data = await orm_get_seizures_for_a_specific_period(
        session, int(current_profile.split('|')[0]), current_year, current_month
    )
    if len(seizures_data) == 0:
        return ChartBuildResult(error=t("analytics.no_chart_data"))
    for seizure in seizures_data:
        date = datetime.strptime(seizure.date, "%Y-%m-%d")
        if date.day in days_range:
            count_seizures_by_days[date.day - 1] += 1
    make_a_gist(
        title=t("analytics.chart_seizures_for_month", month=current_month_in_russian),
        label_x=t("analytics.chart_axis_day"),
        label_y=t("analytics.chart_axis_seizure_count"),
        dataX=days_range,
        dataY=count_seizures_by_days,
        xticks=days_range,
    )
    path = f"temp_images/{chat_id}-{current_profile.split('|', 1)[0]}-{current_date.date()}-{uuid4().hex}.jpg"
    plt.savefig(path)
    plt.close()
    return ChartBuildResult(
        image_path=path,
        caption=t(
            "analytics.caption_month_gist",
            month=current_month_in_russian,
            profile_name=current_profile.split('|')[1],
        ),
    )

def make_a_gist_with_courses(
    title,
    label_x,
    label_y,
    dataX,
    dataY,
    xticks,
    medication_spans=None
):
    rcParams['font.family'] = 'Lato'
    plt.figure(figsize=(10, 6))
    plt.xlabel(label_x, fontproperties='Lato', fontsize=14)
    plt.ylabel(label_y, fontproperties='Lato', fontsize=14)
    plt.title(title, fontproperties='Lato', fontsize=18)
    plt.xticks(ticks=dataX, labels=xticks, fontsize=10)
    ax = plt.gca()
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.ylim(0, max(dataY) + 5)
    plt.grid(visible=True, which='both', linestyle='--', linewidth=0.5)
    if medication_spans:
        for i, (start_month, end_month, color, label) in enumerate(medication_spans):
            ax.axvspan(start_month - 0.5, end_month + 0.5, color=color, alpha=0.2, label=label)

        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), fontsize=9)
    return plt.bar(dataX, dataY)

def extract_course_spans(
    courses: list[MedicationCourse],
    year: int,
    seizures: list[Seizure]
) -> list[tuple]:
    spans = []
    color_palette = ['#AED6F1', '#F9E79F', '#F5B7B1', '#D2B4DE', '#A3E4D7', '#FADBD8']
    current_year = date.today().year
    seizure_months = [
        datetime.strptime(seizure.date, "%Y-%m-%d").month
        for seizure in seizures
        if seizure.date and seizure.date.startswith(str(year))
    ]
    latest_seizure_month = max(seizure_months) if seizure_months else 12
    for idx, course in enumerate(courses):
        if course.start_date.year > year:
            continue
        if course.end_date and course.end_date.year < year:
            continue
        start_month = course.start_date.month if course.start_date.year == year else 1
        if course.end_date:
            end_month = course.end_date.month if course.end_date.year == year else 12
        else:
            if year < current_year:
                end_month = 12
            else:
                end_month = latest_seizure_month

        color = color_palette[idx % len(color_palette)]
        label = f"{course.medication_name} ({course.start_date.strftime('%b')})"
        spans.append((start_month, end_month, color, label))
    return spans

async def get_year_gist_with_courses(session: AsyncSession, chat_id: int, command_text: str) -> ChartBuildResult:
    current_profile = await get_cached_current_profile(session, chat_id)
    if current_profile is None:
        return ChartBuildResult(error=t("analytics.select_profile"))
    profile_id = int(current_profile.split('|', 1)[0])
    profile_name = current_profile.split('|', 1)[1]
    try:
        command_parts = command_text.strip().split('_')
        if len(command_parts) < 3 or not command_parts[-1].isdigit():
            raise ValueError
        current_year = int(command_parts[-1])
    except ValueError:
        return ChartBuildResult(error=t("analytics.invalid_command_format"))
    seizure_data = await orm_get_seizures_for_a_specific_year(session, profile_id, current_year)
    if len(seizure_data) == 0:
        return ChartBuildResult(error=t("analytics.no_data_for_year", year=current_year))
    month_arr = range(1, 13)
    count_seizures_by_month = [0] * 12
    for seizure in seizure_data:
        try:
            date_obj = datetime.strptime(seizure.date, "%Y-%m-%d")
            count_seizures_by_month[date_obj.month - 1] += 1
        except ValueError:
            continue
    course_list = await list_profile_medications(session, profile_id)
    med_spans = extract_course_spans(course_list, current_year, seizure_data)
    make_a_gist_with_courses(
        title=t("analytics.chart_seizures_frequency_year", year=current_year),
        label_x=t("analytics.chart_axis_month"),
        label_y=t("analytics.chart_axis_seizure_count"),
        dataX=month_arr,
        dataY=count_seizures_by_month,
        xticks=MONTHS_RU,
        medication_spans=med_spans,
    )
    path = f"temp_images/gist_eff_{current_year}.png"
    plt.savefig(path)
    plt.close()
    return ChartBuildResult(
        image_path=path,
        caption=t(
            "analytics.caption_drug_efficiency",
            year=current_year,
            profile_name=profile_name,
        ),
    )

async def get_hour_distribution_plot(session: AsyncSession, chat_id: int) -> ChartBuildResult:
    profile = await get_cached_current_profile(session, chat_id)
    if not profile:
        return ChartBuildResult(error=t("analytics.select_profile_first"))
    profile_id = int(profile.split('|', 1)[0])
    profile_name = profile.split('|', 1)[1]
    seizures = await orm_get_seizures_by_profile_ascending(session, profile_id)
    if not seizures:
        return ChartBuildResult(error=t("analytics.no_seizure_data"))
    hourly_distribution = [0] * 24
    for s in seizures:
        if s.time:
            try:
                hour = datetime.strptime(s.time.strip(), "%H:%M").hour
                hourly_distribution[hour] += 1
            except ValueError:
                continue
    rcParams['font.family'] = 'Lato'
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    ax.plot(range(24), hourly_distribution, marker='o', color='#3498DB', linewidth=2)
    plt.xticks(ticks=range(24), labels=[f"{h}:00" for h in range(24)], rotation=45)
    plt.xlabel(t("analytics.chart_axis_hour"))
    plt.ylabel(t("analytics.chart_axis_seizure_count"))
    plt.title(t("analytics.chart_seizures_by_hour"), fontsize=16)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.grid(True, linestyle='--', alpha=0.5)
    path = f"temp_images/seizure_hours_{uuid4()}.png"
    plt.savefig(path)
    plt.close()
    return ChartBuildResult(
        image_path=path,
        caption=t("analytics.caption_hour_distribution", profile_name=profile_name),
    )


async def get_weekday_distribution_plot(session: AsyncSession, chat_id: int) -> ChartBuildResult:
    profile = await get_cached_current_profile(session, chat_id)
    if not profile:
        return ChartBuildResult(error=t("analytics.select_profile_first"))
    profile_id = int(profile.split('|', 1)[0])
    profile_name = profile.split('|', 1)[1]
    seizures = await orm_get_seizures_by_profile_ascending(session, profile_id)
    if not seizures:
        return ChartBuildResult(error=t("analytics.no_seizure_data_analysis"))
    weekday_counts = [0] * 7
    for s in seizures:
        try:
            seizure_date = datetime.strptime(s.date, "%Y-%m-%d")
            weekday = seizure_date.weekday()
            weekday_counts[weekday] += 1
        except Exception:
            continue
    rcParams['font.family'] = 'Lato'
    plt.figure(figsize=(9, 6))
    ax = plt.gca()
    ax.plot(range(7), weekday_counts, marker='o', color='#17A589', linewidth=2)
    plt.xticks(ticks=range(7), labels=WEEKDAYS_RU)
    plt.xlabel(t("analytics.chart_axis_weekday"))
    plt.ylabel(t("analytics.chart_axis_seizure_count"))
    plt.title(t("analytics.chart_seizures_by_weekday"), fontsize=16)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.grid(True, linestyle='--', alpha=0.5)
    path = f"temp_images/seizure_weekdays_{profile_id}.png"
    plt.savefig(path)
    plt.close()
    return ChartBuildResult(
        image_path=path,
        caption=t("analytics.caption_weekday_distribution", profile_name=profile_name),
    )

async def get_month_distribution_plot(session: AsyncSession, chat_id: int) -> ChartBuildResult:
    profile = await get_cached_current_profile(session, chat_id)
    if not profile:
        return ChartBuildResult(error=t("analytics.select_profile_first"))
    profile_id = int(profile.split('|', 1)[0])
    profile_name = profile.split('|', 1)[1]
    seizures = await orm_get_seizures_by_profile_ascending(session, profile_id)
    if not seizures:
        return ChartBuildResult(error=t("analytics.no_analysis_data"))
    month_counts = [0] * 12
    for s in seizures:
        try:
            dt = datetime.strptime(s.date, "%Y-%m-%d")
            month_counts[dt.month - 1] += 1
        except Exception:
            continue
    rcParams['font.family'] = 'Lato'
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    ax.plot(range(12), month_counts, marker='o', color='#884EA0', linewidth=2)
    plt.xticks(ticks=range(12), labels=MONTHS_RU)
    plt.xlabel(t("analytics.chart_axis_month"))
    plt.ylabel(t("analytics.chart_axis_seizure_count"))
    plt.title(t("analytics.chart_seizures_by_month_all_years"), fontsize=16)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.grid(True, linestyle='--', alpha=0.5)
    path = f"temp_images/seizure_months_{profile_id}.png"
    plt.savefig(path)
    plt.close()
    return ChartBuildResult(
        image_path=path,
        caption=t("analytics.caption_month_distribution", profile_name=profile_name),
    )

#STATS
def draw_avg_duration_bar_chart(data, year, profile_name) -> str:
    months = list(range(1, 13))
    avg_by_month = {month: 0 for month in months}
    for month, avg in data:
        avg_by_month[int(month)] = round(avg)
    values = [avg_by_month[m] for m in months]
    plt.figure(figsize=(10, 6))
    bars = plt.bar(months, values, color="skyblue")
    plt.xticks(months, MONTHS_RU)
    plt.title(t("analytics.chart_avg_duration_by_month", year=year), fontsize=14)
    plt.ylabel(t("analytics.chart_axis_avg_duration_sec"))
    plt.xlabel(t("analytics.chart_axis_month"))
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.ylim(0, max(values) + 10)
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            plt.text(bar.get_x() + bar.get_width()/2, height + 1, f"{int(height)}", ha="center", va="bottom")
    path = f"temp_images/duration_avg_{year}.png"
    os.makedirs("temp_images", exist_ok=True)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path

async def compute_seizure_statistics(session: AsyncSession, chat_id: int) -> dict:
    profile = await get_cached_current_profile(session, chat_id)
    if not profile:
        return {"error": t("analytics.select_profile_first")}
    profile_id = int(profile.split("|")[0])
    profile_name = profile.split("|")[1]
    seizures = await orm_get_seizures_by_profile_ascending(session, profile_id)
    if len(seizures) < 1:
        return {"error": t("analytics.no_analysis_data")}
    durations = []
    dates = []
    now = await get_user_local_datetime(session, chat_id)
    for s in seizures:
        try:
            d = datetime.strptime(s.date, "%Y-%m-%d")
            dates.append(d)
            if s.duration:
                durations.append(s.duration)
        except Exception:
            continue
    dates.sort()
    if durations:
        dur_array = np.array(durations)
        dur_mean = np.mean(dur_array)
        dur_std = np.std(dur_array)
        dur_ci = stats.norm.interval(0.95, loc=dur_mean, scale=dur_std / np.sqrt(len(durations))) if len(durations) > 1 else None
        min_dur = min(durations)
        max_dur = max(durations)
    else:
        dur_mean = dur_std = dur_ci = min_dur = max_dur = None
    total_days = (dates[-1].date() - dates[0].date()).days + 1
    total_months = total_days / 30.44 if total_days > 0 else 1
    total_count = len(dates)
    freq = total_count / total_months
    if total_count > 30:
        freq_ci = stats.norm.interval(0.95, loc=freq, scale=freq / np.sqrt(total_count))
    else:
        freq_ci = None
    days_without_seizures = (now.date() - dates[-1].date()).days
    gaps = [
        (dates[i + 1] - dates[i]).days
        for i in range(len(dates) - 1)
    ]
    avg_days_between = int(sum(gaps) / len(gaps)) if gaps else 0
    def avg_duration_since(start_date: date):
        filtered = [s for s in seizures if datetime.strptime(s.date, "%Y-%m-%d").date() >= start_date and s.duration]
        if not filtered:
            return None
        return int(sum(s.duration for s in filtered) / len(filtered))
    start_of_week = now.date() - timedelta(days=now.isoweekday() - 1)
    start_of_month = now.replace(day=1).date()
    avg_week = avg_duration_since(start_of_week)
    avg_month = avg_duration_since(start_of_month)
    return {
        "profile_name": profile_name,
        "total_count": total_count,
        "total_months": round(total_months, 1),
        "days_without_seizures": days_without_seizures,
        "avg_days_without_seizures": avg_days_between,
        "duration_mean": dur_mean,
        "duration_ci": dur_ci,
        "min_duration": min_dur,
        "max_duration": max_dur,
        "avg_week": avg_week,
        "avg_month": avg_month,
        "freq": freq,
        "freq_ci": freq_ci
    }

def format_seizure_statistics(stats: dict) -> str:
    text = t("analytics.stats_header", profile_name=stats['profile_name'])
    text += t("analytics.stats_total", count=stats['total_count'])
    text += t("analytics.stats_period", months=stats['total_months'])
    text += t("analytics.stats_days_without", days=stats['days_without_seizures'])
    text += t("analytics.stats_avg_interval", days=stats['avg_days_without_seizures'])
    if stats['freq_ci']:
        text += t(
            "analytics.stats_frequency_ci",
            freq=stats['freq'],
            ci_low=stats['freq_ci'][0],
            ci_high=stats['freq_ci'][1],
        ) + "\n\n"
    else:
        text += t("analytics.stats_frequency", freq=stats['freq'])
    if stats['duration_mean']:
        text += t(
            "analytics.stats_avg_duration",
            duration=get_minutes_and_seconds(int(stats['duration_mean'])),
        )
        if stats['duration_ci']:
            text += t(
                "analytics.stats_duration_ci",
                low=get_minutes_and_seconds(int(stats['duration_ci'][0])),
                high=get_minutes_and_seconds(int(stats['duration_ci'][1])),
            )
        text += t(
            "analytics.stats_duration_min_max",
            min_duration=get_minutes_and_seconds(stats['min_duration']),
            max_duration=get_minutes_and_seconds(stats['max_duration']),
        )
    if stats['avg_week'] is not None:
        text += t("analytics.stats_avg_week", duration=get_minutes_and_seconds(stats['avg_week']))
    if stats['avg_month'] is not None:
        text += t("analytics.stats_avg_month", duration=get_minutes_and_seconds(stats['avg_month']))
    return text


def format_top_features(profile_name: str, top_symptoms: list, top_triggers: list, top_types: list) -> str:
    text = t("analytics.features_header", profile_name=profile_name)
    if top_symptoms:
        text += t("analytics.features_symptoms_header")
        for i, item in enumerate(top_symptoms, start=1):
            text += t("analytics.features_symptoms_item", index=i, name=item['name'], count=item['count'])
    else:
        text += t("analytics.features_symptoms_empty")
    text += "\n"
    if top_triggers:
        text += t("analytics.features_triggers_header")
        for i, item in enumerate(top_triggers, start=1):
            text += t("analytics.features_triggers_item", index=i, name=item['name'], count=item['count'])
    else:
        text += t("analytics.features_triggers_empty")
    text += "\n"
    if top_types:
        text += t("analytics.features_types_header")
        for i, item in enumerate(top_types, start=1):
            text += t("analytics.features_types_item", index=i, name=item['name'], count=item['count'])
    else:
        text += t("analytics.features_types_empty")
    return text