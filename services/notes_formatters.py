from aiogram.types import Message
from aiogram import Bot
from decimal import Decimal, InvalidOperation

from database.models import Trigger

async def get_formatted_seizure_info(
    seizure_id,
    current_profile,
    date,
    time,
    count,
    triggers,
    severity,
    duration,
    comment,
    symptoms,
    video_tg_id,
    bot: Bot,
    message: Message,
    location: str = None,
    type_of_seizure: str = None,
    medication: str = None,
    edit_mode: bool = False
):
    def is_decimal(s):
        try:
            Decimal(s)
            return True
        except InvalidOperation:
            return False
    def get_emoji_or_text(geo):
        if (geo is not None) and (len(geo.split('|', 1)) == 2):
            lat, long = geo.split('|', 1)
            if is_decimal(lat) and is_decimal(long):
                return "✅"
        else:
            return geo

    action_lines = (
        f"\n_______________________________________"
        f"\n\n✍️ Редактировать запись: /sjedit_{seizure_id}\n\n"
        f"🗑️ Удалить запись: /delete_{seizure_id}"
    )
    #suus = f" {'/update_date_' + {seizure_id} + '\n\n' if sjedit_mode else ""}"
    note = (
        f"Данные о приступе для профиля {current_profile}:\n\n"


        f"📅 Дата: {date if date else "Не введено"}" +
        f"{' /update_date_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"⌚ Время: {time if time else "Не введено"}" +
         f"{' /update_time_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"🧮 Количество: {count if count else "Не введено"}" +
        f"{' /update_count_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"⚡ Тип припадка: {type_of_seizure if type_of_seizure else 'Не введено'}" +
        f"{' /update_type_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"💥 Триггеры: {triggers if triggers else "Не введено"}" +
        f"{' /update_triggers_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"😓 Тяжесть: {str(severity) + ' баллов ' if severity else "Не введено"}" +
        f"{' /update_severity_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"⏱️ Продолжительность: {str(duration) if duration else "Не введено"}" +
        f"{' /update_duration_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"📝 Комментарий: {comment if comment else "Не введено"}" +
        f"{' /update_comment_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"🧠 Симптомы: {symptoms if symptoms else "Не введено"}" +
        f"{' /update_symptoms_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"🎦 Видео: {"✅" if video_tg_id else '❌'}" +
        f"{' /update_video_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"📍 Место: {"❌" if (location is None) or (len(location.strip()) == 0) else get_emoji_or_text(location)}" +
        f"{' /update_location_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"💊 Принимаемый курс лекарств: {medication + '\n' if medication else 'Не введено'}" +
        f"{' /update_medication_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"{action_lines if seizure_id > 0 else ""}"
        )
    await message.answer(note, parse_mode='HTML')
    if not edit_mode:
        if video_tg_id != None:
            await bot.send_video(chat_id=message.chat.id, video=video_tg_id)
        if (location is not None) and (get_emoji_or_text(location) == "✅"):
            latitude, longitude = location.split('|', 1)
            await bot.send_location(message.chat.id, float(latitude), float(longitude))

def get_minutes_and_seconds(seconds: int) -> str:
    if seconds is None:
        return None
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} сек."
    elif seconds == 60:
        return f"1 мин."
    else:
        return f"{seconds // 60} мин. {seconds % 60} сек."

def get_stats_info(
    total_count,
    days_without_seizures,
    avg_days_without_seizures,
    total_avg_duration,
    min_max_duration,
    avg_duration_week,
    avg_duration_month
    ):
    min_duration = min_max_duration.split('|', 1)[0] if min_max_duration is not None else None
    max_duration = min_max_duration.split('|', 1)[1] if min_max_duration is not None else None
    text = (
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
):
    header = (
        f"Данные по профилю {profile_name}\n\n"
    )
    action_lines = (
        f"\nРедактировать данные профиля: /editp_{profile_id}\n\n"
        f"Удалить профиль: /deletep_{profile_id}"
    )
    text = (
        f"Вид: {bio_species if bio_species else ""}\n"
        f"Тип эпилепсии: {type_of_epilepsy if type_of_epilepsy else ""}\n"
        f"Возраст: {str(age) if age else ""}\n"
        f"Пол: {sex if sex else ""}\n"
    )