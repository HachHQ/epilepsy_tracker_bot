from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


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
        return f"{seconds} сек."
    if seconds == 60:
        return "1 мин."
    return f"{seconds // 60} мин. {seconds % 60} сек."


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
    action_lines = (
        "\n_______________________________________"
        "\n\n✍️ Редактировать запись: /sjedit_{seizure_id}\n\n"
        "🗑️ Удалить запись: /delete_{seizure_id}"
    ).format(seizure_id=seizure_id)

    note = (
        f"Данные о приступе для профиля {current_profile}:\n\n"
        f"📅 Дата: {date if date else 'Не введено'}"
        f"{' /update_date_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"⌚ Время: {time if time else 'Не введено'}"
        f"{' /update_time_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"🧮 Количество: {count if count else 'Не введено'}"
        f"{' /update_count_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"⚡ Тип припадка: {type_of_seizure if type_of_seizure else 'Не введено'}"
        f"{' /update_type_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"💥 Триггеры: {triggers if triggers else 'Не введено'}"
        f"{' /update_triggers_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"😓 Тяжесть: {str(severity) + ' баллов ' if severity else 'Не введено'}"
        f"{' /update_severity_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"⏱️ Продолжительность: {str(duration) if duration else 'Не введено'}"
        f"{' /update_duration_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"📝 Комментарий: {comment if comment else 'Не введено'}"
        f"{' /update_comment_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"🧠 Симптомы: {symptoms if symptoms else 'Не введено'}"
        f"{' /update_symptoms_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"🎦 Видео: {'✅' if video_tg_id else '❌'}"
        f"{' /update_video_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"📍 Место: {'❌' if (location is None) or (len(location.strip()) == 0) else _location_marker(location)}"
        f"{' /update_location_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"💊 Принимаемый курс лекарств: {medication + chr(10) if medication else 'Не введено'}"
        f"{' /update_medication_' + str(seizure_id) + chr(10) if edit_mode else chr(10)}"
        f"{action_lines if seizure_id > 0 else ''}"
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
        f"Всего приступов: {total_count}\n\n"
        f"Дней без приступов: {days_without_seizures}\n\n"
        f"Дней без приступов в среднем {avg_days_without_seizures}\n\n"
        f"Средняя продолжительность: {total_avg_duration}\n\n"
        f"Минимальная и максимальная продолжительность: {min_duration} | {max_duration}\n\n"
        f"Средняя продолжительность за последнюю неделю: {avg_duration_week}\n\n"
        f"Средняя продолжительность за последний месяц: {avg_duration_month}\n\n"
    )


def get_formatted_profile_info(
    profile_id: int,
    profile_name: str,
    bio_species,
    type_of_epilepsy: str,
    age: int,
    sex: str,
) -> str:
    return (
        f"Данные по профилю {profile_name}\n\n"
        f"Вид: {bio_species if bio_species else ''}\n"
        f"Тип эпилепсии: {type_of_epilepsy if type_of_epilepsy else ''}\n"
        f"Возраст: {str(age) if age else ''}\n"
        f"Пол: {sex if sex else ''}\n"
        f"\nРедактировать данные профиля: /editp_{profile_id}\n\n"
        f"Удалить профиль: /deletep_{profile_id}"
    )
