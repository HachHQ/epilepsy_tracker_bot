def get_formatted_seizure_info(
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
    location,
    type_of_seizure: str = None,
    medication: str = None,
    edit_mode: bool = False
):
    action_lines = (
        f"\n_______________________________________"
        f"\n\n✍️ Редактировать запись: /edit_{seizure_id}\n\n"
        f"🗑️ Удалить запись: /delete_{seizure_id}"
    )
    #suus = f" {'/update_date_' + {seizure_id} + '\n\n' if edit_mode else ""}"
    note = (
        f"Данные о приступе для профиля {current_profile}:\n\n"


        f"📅 Дата: {date if date else "Не введено"}" +
        f"{' /update_date_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"⌚ Время: {time if time else "Не введено"}" +
         f"{' /update_time_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"🧮 Количество: {count if count else "Не введено"}" +
        f"{' /update_count_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"⚡ Тип припадка: {type_of_seizure + '\n' if type_of_seizure else 'Не введено'}" +
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

        f"🎞️ Видео: {"✅" if video_tg_id else '❌'}" +
        f"{' /update_video_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"🗺️ Место: {"✅" if location else "❌"}" +
        f"{' /update_location_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"💊 Принимаемый курс лекарств: {medication + '\n' if medication else 'Не введено'}" +
        f"{' /update_medication_' + str(seizure_id) + '\n' if edit_mode else "\n"}"

        f"{action_lines if seizure_id > 0 else ""}"
        )
    return note

def get_minutes_and_seconds(seconds: int) -> str:
    if seconds is None:
        return None
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} секунд"
    elif seconds == 60:
        return f"1 минута"
    else:
        return f"{seconds // 60} минут {seconds % 60} секунд"

def get_formatted_profile_info(
    profile_id: int,
    profile_name: str,
    bio_species,
    type_of_epilepsy: str,
    age: int,
    sex: str,
    timezone
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
        f"Часовой пояс: {timezone if timezone else ""}\n"
    )