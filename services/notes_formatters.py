from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from i18n import t


@dataclass(frozen=True)
class SeizureDisplayPayload:
    text: str
    video_tg_id: str | None
    location: str | None


def get_minutes_and_seconds(seconds: int) -> str:
    if seconds is None:
        return None
    seconds = int(seconds)
    if seconds < 60:
        return t("notes.duration_seconds", seconds=seconds)
    if seconds == 60:
        return t("notes.duration_one_minute")
    return t("notes.duration_minutes_seconds", minutes=seconds // 60, seconds=seconds % 60)


def _is_decimal(value: str) -> bool:
    try:
        Decimal(value)
        return True
    except InvalidOperation:
        return False


def _location_marker(location: str | None) -> str:
    if location is None:
        return "❌"
    if len(location.split("|", 1)) == 2:
        lat, long = location.split("|", 1)
        if _is_decimal(lat) and _is_decimal(long):
            return "✅"
    return location


def parse_location_coords(location: str | None) -> tuple[float, float] | None:
    if location is None:
        return None
    parts = location.split("|", 1)
    if len(parts) != 2:
        return None
    lat, long = parts
    if _is_decimal(lat) and _is_decimal(long):
        return float(lat), float(long)
    return None


def _field_line(label_key: str, value, edit_mode: bool, update_cmd: str) -> str:
    display = value if value else t("notes.not_entered")
    suffix = f" {update_cmd}{chr(10)}" if edit_mode else chr(10)
    return t(label_key, value=display) + suffix


def build_seizure_display(
    *,
    seizure_id: int,
    current_profile: str,
    date,
    time,
    count,
    triggers,
    severity,
    duration,
    comment,
    symptoms,
    video_tg_id,
    location: str | None = None,
    type_of_seizure: str | None = None,
    medication: str | None = None,
    edit_mode: bool = False,
) -> SeizureDisplayPayload:
    not_entered = t("notes.not_entered")
    severity_display = (
        t("notes.severity_points", severity=severity) if severity else not_entered
    )
    video_display = "✅" if video_tg_id else "❌"
    if location is None or len(location.strip()) == 0:
        location_display = "❌"
    else:
        location_display = _location_marker(location)
    medication_display = medication if medication else not_entered

    note = t("notes.seizure_header", profile=current_profile)
    note += _field_line("notes.field_date", date, edit_mode, f"/update_date_{seizure_id}")
    note += _field_line("notes.field_time", time, edit_mode, f"/update_time_{seizure_id}")
    note += _field_line("notes.field_count", count, edit_mode, f"/update_count_{seizure_id}")
    note += _field_line("notes.field_type", type_of_seizure, edit_mode, f"/update_type_{seizure_id}")
    note += _field_line("notes.field_triggers", triggers, edit_mode, f"/update_triggers_{seizure_id}")
    note += t("notes.field_severity", value=severity_display)
    note += (f" /update_severity_{seizure_id}{chr(10)}" if edit_mode else chr(10))
    note += _field_line("notes.field_duration", duration, edit_mode, f"/update_duration_{seizure_id}")
    note += _field_line("notes.field_comment", comment, edit_mode, f"/update_comment_{seizure_id}")
    note += _field_line("notes.field_symptoms", symptoms, edit_mode, f"/update_symptoms_{seizure_id}")
    note += t("notes.field_video", value=video_display)
    note += (f" /update_video_{seizure_id}{chr(10)}" if edit_mode else chr(10))
    note += t("notes.field_location", value=location_display)
    note += (f" /update_location_{seizure_id}{chr(10)}" if edit_mode else chr(10))
    note += t("notes.field_medication", value=medication_display)
    note += (f" /update_medication_{seizure_id}{chr(10)}" if edit_mode else chr(10))

    if seizure_id > 0:
        note += (
            "\n_______________________________________\n\n"
            + t("notes.edit_record", seizure_id=seizure_id)
            + "\n\n"
            + t("notes.delete_record", seizure_id=seizure_id)
        )

    return SeizureDisplayPayload(text=note, video_tg_id=video_tg_id, location=location)


def get_stats_info(
    total_count,
    days_without_seizures,
    avg_days_without_seizures,
    total_avg_duration,
    min_max_duration,
    avg_duration_week,
    avg_duration_month,
):
    min_duration = min_max_duration.split("|", 1)[0] if min_max_duration is not None else None
    max_duration = min_max_duration.split("|", 1)[1] if min_max_duration is not None else None
    return (
        t("notes.stats_total", count=total_count)
        + t("notes.stats_days_without", days=days_without_seizures)
        + t("notes.stats_avg_days_without", days=avg_days_without_seizures)
        + t("notes.stats_avg_duration", duration=total_avg_duration)
        + t("notes.stats_min_max_duration", min_duration=min_duration, max_duration=max_duration)
        + t("notes.stats_avg_duration_week", duration=avg_duration_week)
        + t("notes.stats_avg_duration_month", duration=avg_duration_month)
    )


def get_formatted_profile_info(
    profile_id: int,
    profile_name: str,
    bio_species,
    type_of_epilepsy: str,
    age: int,
    sex: str,
) -> str:
    empty = ""
    return (
        t("notes.profile_header", profile_name=profile_name)
        + t("notes.profile_species", value=bio_species if bio_species else empty) + "\n"
        + t("notes.profile_epilepsy_type", value=type_of_epilepsy if type_of_epilepsy else empty) + "\n"
        + t("notes.profile_age", value=str(age) if age else empty) + "\n"
        + t("notes.profile_sex", value=sex if sex else empty) + "\n"
        + f"\n{t('notes.profile_edit', profile_id=profile_id)}\n\n"
        + t("notes.profile_delete", profile_id=profile_id)
    )
