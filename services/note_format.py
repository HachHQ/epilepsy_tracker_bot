def get_formatted_seizure_info(
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
    seizure_id: int = 0
):
    action_lines = (
        f"\n________________________________________"
        f"\n\n✍️ Редактировать запись: /edit_{seizure_id}\n\n"
        f"🗑️ Удалить запись: /delete_{seizure_id}"
    )
    note = (
        f"Данные о приступе для профиля <u>{current_profile}</u>:\n\n"
        f"📅 Дата: {date if date else "Не введено"}\n"
        f"⌚ Время: {time if time else "Не введено"}\n"
        f"🧮 Количество: {count if count else "Не введено"}\n"
        f"{'⚡ Тип припадка: ' + type_of_seizure + '\n' if type_of_seizure else ''}"
        f"💥 Триггеры: {triggers if triggers else "Не введено"}\n"
        f"😓 Тяжесть: {str(severity) + ' баллов ' if severity else "Не введено"}\n"
        f"⏱️ Продолжительность: {str(duration) + ' минут ' if duration else "Не введено"}\n"
        f"📝 Комментарий: {comment if comment else "Не введено"}\n"
        f"🧠 Симптомы: {symptoms if symptoms else "Не введено"}\n"
        f"🎞️ Видео: {"✅" if video_tg_id else '❌'}\n"
        f"🗺️ Место: {"✅" if location else "❌"}"
        f"{'💊 Принимаемый курс лекарств: ' + medication + '\n' if medication else ''}"
        f"{action_lines if seizure_id > 0 else ""}"
    )
    return note

def get_formatted_seizure_edit(
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
        f"\n________________________________________"
        f"\n\n✍️ Редактировать запись: /edit_{seizure_id}\n\n"
        f"🗑️ Удалить запись: /delete_{seizure_id}"
    )
    #suus = f" {'/update_date_' + {seizure_id} + '\n\n' if edit_mode else ""}"
    note = (
        f"Данные о приступе для профиля <u>{current_profile}</u>:\n\n"

        f"📅 Дата: {date if date else "Не введено"}\n" + f"{'/update_date_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"⌚ Время: {time if time else "Не введено"}\n" + f"{' /update_time_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"🧮 Количество: {count if count else "Не введено"}\n" + f"{'/update_count_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"'⚡ Тип припадка: '{type_of_seizure + '\n' if type_of_seizure else 'Не введено'}\n" + f"{'/update_type_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"💥 Триггеры: {triggers if triggers else "Не введено"}\n" + f"{'/update_triggers_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"😓 Тяжесть: {str(severity) + ' баллов ' if severity else "Не введено"}\n" + f"{'/update_severity_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"⏱️ Продолжительность: {str(duration) + ' минут ' if duration else "Не введено"}\n" + f"{'/update_duration_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"📝 Комментарий: {comment if comment else "Не введено"}\n" + f"{'/update_comment_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"🧠 Симптомы: {symptoms if symptoms else "Не введено"}\n" + f"{'/update_symptoms_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"🎞️ Видео: {"✅" if video_tg_id else '❌'}\n" + f"{'/update_video_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"🗺️ Место: {"✅" if location else "❌"}\n" + f"{'/update_location_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"💊 Принимаемый курс лекарств: {medication + '\n' if medication else 'Не введено'}\n" + f"{'/update_medication_' + str(seizure_id) + '\n\n' if edit_mode else ""}"

        f"{action_lines if seizure_id > 0 else ""}"
        )
    return note
