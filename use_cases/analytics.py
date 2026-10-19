from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

import numpy as np
from scipy import stats
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.analytics import get_avg_duration_by_month, get_top_seizure_features
from database.repositories.medications import list_profile_medications
from database.repositories.seizures import (
    list_profile_seizures,
    list_seizures_for_year,
    list_seizures_from_date,
)
from i18n import get_month_abbreviations, t
from services.profile_ref import ProfileRef
from services.redis_cache_data import get_user_local_datetime


@dataclass(frozen=True)
class SeizurePoint:
    on_date: date | None
    at_time: time | None
    duration: int | None


@dataclass(frozen=True)
class MonthCountSeries:
    profile_name: str
    year: int
    counts: tuple[int, ...]
    error: str | None = None


@dataclass(frozen=True)
class DayCountSeries:
    profile_name: str
    profile_id: int
    counts: tuple[int, ...]
    month_label: str
    stamp: date
    error: str | None = None


@dataclass(frozen=True)
class CourseSpan:
    start_month: int
    end_month: int
    color: str
    label: str


@dataclass(frozen=True)
class EfficiencySeries:
    profile_name: str
    year: int
    counts: tuple[int, ...]
    spans: tuple[CourseSpan, ...]
    error: str | None = None


@dataclass(frozen=True)
class DistributionSeries:
    profile_name: str
    profile_id: int
    counts: tuple[int, ...]
    error: str | None = None


def seizure_point(seizure) -> SeizurePoint:
    return SeizurePoint(
        on_date=_as_date(getattr(seizure, "date", None)),
        at_time=_as_time(getattr(seizure, "time", None)),
        duration=getattr(seizure, "duration", None),
    )


def _as_date(raw) -> date | None:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _as_time(raw) -> time | None:
    if isinstance(raw, datetime):
        return raw.time().replace(microsecond=0)
    if isinstance(raw, time):
        return raw.replace(microsecond=0)
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.strptime(raw.strip(), "%H:%M").time()
        except ValueError:
            return None
    return None


def _month_counts(points: list[SeizurePoint], year: int | None = None) -> tuple[int, ...]:
    counts = [0] * 12
    for point in points:
        if point.on_date is None:
            continue
        if year is not None and point.on_date.year != year:
            continue
        counts[point.on_date.month - 1] += 1
    return tuple(counts)


def course_spans(courses, year: int, points: list[SeizurePoint]) -> tuple[CourseSpan, ...]:
    spans: list[CourseSpan] = []
    color_palette = ["#AED6F1", "#F9E79F", "#F5B7B1", "#D2B4DE", "#A3E4D7", "#FADBD8"]
    current_year = date.today().year
    seizure_months = [point.on_date.month for point in points if point.on_date and point.on_date.year == year]
    latest_seizure_month = max(seizure_months) if seizure_months else 12
    for idx, course in enumerate(courses):
        if course.start_date.year > year:
            continue
        if course.end_date and course.end_date.year < year:
            continue
        start_month = course.start_date.month if course.start_date.year == year else 1
        if course.end_date:
            end_month = course.end_date.month if course.end_date.year == year else 12
        elif year < current_year:
            end_month = 12
        else:
            end_month = latest_seizure_month
        spans.append(
            CourseSpan(
                start_month=start_month,
                end_month=end_month,
                color=color_palette[idx % len(color_palette)],
                label=f"{course.medication_name} ({course.start_date.strftime('%b')})",
            )
        )
    return tuple(spans)


async def get_profile_feature_stats(session: AsyncSession, profile_id: int) -> dict:
    return await get_top_seizure_features(session, profile_id)


async def get_monthly_avg_duration(session: AsyncSession, profile_id: int, year: int):
    return await get_avg_duration_by_month(session, profile_id, year)


async def build_year_counts(session: AsyncSession, profile: ProfileRef | None) -> MonthCountSeries:
    year = datetime.now(UTC).year
    if profile is None:
        return MonthCountSeries("", year, (), error=t("analytics.select_profile"))
    seizures = await list_seizures_from_date(session, profile.id, year=year)
    if not seizures:
        return MonthCountSeries(profile.name, year, (), error=t("analytics.no_chart_data"))
    return MonthCountSeries(profile.name, year, _month_counts([seizure_point(item) for item in seizures], year))


async def build_month_counts(session: AsyncSession, profile: ProfileRef | None) -> DayCountSeries:
    today = datetime.now(UTC).date()
    if profile is None:
        return DayCountSeries("", 0, (), "", today, error=t("analytics.select_profile"))
    seizures = await list_seizures_from_date(session, profile.id, year=today.year, month=today.month)
    if not seizures:
        return DayCountSeries(profile.name, profile.id, (), "", today, error=t("analytics.no_chart_data"))
    days_in_month = calendar_days(today.year, today.month)
    counts = [0] * days_in_month
    for point in (seizure_point(item) for item in seizures):
        if point.on_date and point.on_date.day <= days_in_month:
            counts[point.on_date.day - 1] += 1
    return DayCountSeries(
        profile.name,
        profile.id,
        tuple(counts),
        get_month_abbreviations()[today.month - 1],
        today,
    )


def calendar_days(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days


async def build_efficiency_series(
    session: AsyncSession, profile: ProfileRef | None, command_text: str
) -> EfficiencySeries:
    if profile is None:
        return EfficiencySeries("", 0, (), (), error=t("analytics.select_profile"))
    try:
        command_parts = command_text.strip().split("_")
        if len(command_parts) < 3 or not command_parts[-1].isdigit():
            raise ValueError
        year = int(command_parts[-1])
    except ValueError:
        return EfficiencySeries(profile.name, 0, (), (), error=t("analytics.invalid_command_format"))
    seizures = await list_seizures_for_year(session, profile.id, year)
    if not seizures:
        return EfficiencySeries(profile.name, year, (), (), error=t("analytics.no_data_for_year", year=year))
    points = [seizure_point(item) for item in seizures]
    courses = await list_profile_medications(session, profile.id)
    return EfficiencySeries(profile.name, year, _month_counts(points, year), course_spans(courses, year, points))


async def build_hour_distribution(session: AsyncSession, profile: ProfileRef | None) -> DistributionSeries:
    return await _distribution(session, profile, _hour_counts, t("analytics.no_seizure_data"))


async def build_weekday_distribution(session: AsyncSession, profile: ProfileRef | None) -> DistributionSeries:
    return await _distribution(session, profile, _weekday_counts, t("analytics.no_seizure_data_analysis"))


async def build_calendar_month_distribution(session: AsyncSession, profile: ProfileRef | None) -> DistributionSeries:
    return await _distribution(session, profile, lambda points: _month_counts(points), t("analytics.no_analysis_data"))


async def _distribution(session, profile, counter, empty_error: str) -> DistributionSeries:
    if profile is None:
        return DistributionSeries("", 0, (), error=t("analytics.select_profile_first"))
    seizures = await list_profile_seizures(session, profile.id, descending=False)
    if not seizures:
        return DistributionSeries(profile.name, profile.id, (), error=empty_error)
    return DistributionSeries(
        profile.name,
        profile.id,
        counter([seizure_point(item) for item in seizures]),
        None,
    )


def _hour_counts(points: list[SeizurePoint]) -> tuple[int, ...]:
    counts = [0] * 24
    for point in points:
        if point.at_time is not None:
            counts[point.at_time.hour] += 1
    return tuple(counts)


def _weekday_counts(points: list[SeizurePoint]) -> tuple[int, ...]:
    counts = [0] * 7
    for point in points:
        if point.on_date is not None:
            counts[point.on_date.weekday()] += 1
    return tuple(counts)


async def build_seizure_statistics(
    session: AsyncSession, profile: ProfileRef | None, chat_id: int
) -> dict:
    if profile is None:
        return {"error": t("analytics.select_profile_first")}
    seizures = await list_profile_seizures(session, profile.id, descending=False)
    if len(seizures) < 1:
        return {"error": t("analytics.no_analysis_data")}
    points = [seizure_point(item) for item in seizures]
    dated = [point for point in points if point.on_date is not None]
    if not dated:
        return {"error": t("analytics.no_analysis_data")}
    durations = [point.duration for point in dated if point.duration]
    dates = sorted(point.on_date for point in dated if point.on_date is not None)
    now = await get_user_local_datetime(session, chat_id)
    if durations:
        dur_array = np.array(durations)
        dur_mean = np.mean(dur_array)
        dur_std = np.std(dur_array)
        dur_ci = (
            stats.norm.interval(0.95, loc=dur_mean, scale=dur_std / np.sqrt(len(durations)))
            if len(durations) > 1
            else None
        )
        min_dur = min(durations)
        max_dur = max(durations)
    else:
        dur_mean = None
        dur_ci = None
        min_dur = None
        max_dur = None
    total_days = (dates[-1] - dates[0]).days + 1
    total_months = total_days / 30.44 if total_days > 0 else 1
    total_count = len(dates)
    freq = total_count / total_months
    freq_ci = stats.norm.interval(0.95, loc=freq, scale=freq / np.sqrt(total_count)) if total_count > 30 else None
    days_without_seizures = (now.date() - dates[-1]).days
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    avg_days_between = int(sum(gaps) / len(gaps)) if gaps else 0

    def avg_duration_since(start_date: date):
        filtered = [point.duration for point in dated if point.on_date and point.on_date >= start_date and point.duration]
        if not filtered:
            return None
        return int(sum(filtered) / len(filtered))

    start_of_week = now.date() - timedelta(days=now.isoweekday() - 1)
    start_of_month = now.replace(day=1).date()
    return {
        "profile_name": profile.name,
        "total_count": total_count,
        "total_months": round(total_months, 1),
        "days_without_seizures": days_without_seizures,
        "avg_days_without_seizures": avg_days_between,
        "duration_mean": dur_mean,
        "duration_ci": dur_ci,
        "min_duration": min_dur,
        "max_duration": max_dur,
        "avg_week": avg_duration_since(start_of_week),
        "avg_month": avg_duration_since(start_of_month),
        "freq": freq,
        "freq_ci": freq_ci,
    }
