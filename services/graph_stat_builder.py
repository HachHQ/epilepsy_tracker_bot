import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.ticker import MaxNLocator

from i18n import get_month_abbreviations, get_weekday_abbreviations, t
from services.notes_formatters import get_minutes_and_seconds
from use_cases.analytics import (
    DayCountSeries,
    DistributionSeries,
    EfficiencySeries,
    MonthCountSeries,
)

Path("temp_images").mkdir(exist_ok=True)

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

def render_year_gist(series: MonthCountSeries) -> ChartBuildResult:
    if series.error or not series.counts:
        return ChartBuildResult(error=series.error or t("analytics.no_chart_data"))
    _refresh_chart_labels()
    month_arr = range(1, 13)
    make_a_gist(
        title=t("analytics.chart_seizures_by_month_year", year=series.year),
        label_x=t("analytics.chart_axis_month"),
        label_y=t("analytics.chart_axis_seizure_count"),
        dataX=month_arr,
        dataY=list(series.counts),
        xticks=MONTHS_RU,
    )
    path = "temp_images/gist_year.png"
    plt.savefig(path)
    plt.close()
    return ChartBuildResult(
        image_path=path,
        caption=t(
            "analytics.caption_year_gist",
            year=series.year,
            profile_name=series.profile_name,
        ),
    )

def render_month_gist(series: DayCountSeries) -> ChartBuildResult:
    if series.error or not series.counts:
        return ChartBuildResult(error=series.error or t("analytics.no_chart_data"))
    days_range = list(range(1, len(series.counts) + 1))
    make_a_gist(
        title=t("analytics.chart_seizures_for_month", month=series.month_label),
        label_x=t("analytics.chart_axis_day"),
        label_y=t("analytics.chart_axis_seizure_count"),
        dataX=days_range,
        dataY=list(series.counts),
        xticks=days_range,
    )
    path = f"temp_images/{series.profile_id}-{series.stamp}-{uuid4().hex}.jpg"
    plt.savefig(path)
    plt.close()
    return ChartBuildResult(
        image_path=path,
        caption=t(
            "analytics.caption_month_gist",
            month=series.month_label,
            profile_name=series.profile_name,
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
        for _, (start_month, end_month, color, label) in enumerate(medication_spans):
            ax.axvspan(start_month - 0.5, end_month + 0.5, color=color, alpha=0.2, label=label)

        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles, strict=False))
        ax.legend(by_label.values(), by_label.keys(), fontsize=9)
    return plt.bar(dataX, dataY)

def render_efficiency_gist(series: EfficiencySeries) -> ChartBuildResult:
    if series.error or not series.counts:
        return ChartBuildResult(error=series.error or t("analytics.no_chart_data"))
    _refresh_chart_labels()
    month_arr = range(1, 13)
    med_spans = [
        (span.start_month, span.end_month, span.color, span.label) for span in series.spans
    ]
    current_year = series.year
    profile_name = series.profile_name
    count_seizures_by_month = list(series.counts)
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

def render_hour_distribution(series: DistributionSeries) -> ChartBuildResult:
    if series.error or not series.counts:
        return ChartBuildResult(error=series.error or t("analytics.no_seizure_data"))
    profile_name = series.profile_name
    hourly_distribution = list(series.counts)
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


def render_weekday_distribution(series: DistributionSeries) -> ChartBuildResult:
    if series.error or not series.counts:
        return ChartBuildResult(error=series.error or t("analytics.no_seizure_data_analysis"))
    profile_id = series.profile_id
    profile_name = series.profile_name
    weekday_counts = list(series.counts)
    _refresh_chart_labels()
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

def render_month_distribution(series: DistributionSeries) -> ChartBuildResult:
    if series.error or not series.counts:
        return ChartBuildResult(error=series.error or t("analytics.no_analysis_data"))
    profile_id = series.profile_id
    profile_name = series.profile_name
    month_counts = list(series.counts)
    _refresh_chart_labels()
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