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
    seizure_id: int = 0
):
    action_lines = (
        f"\n________________________________________"
        f"\n\nРедактировать запись: /edit_{seizure_id}\n\n"
        f"Удалить запись: /delete_{seizure_id}"
    )
    text = (f"Данные о приступе для профиля <u>{current_profile}</u>:\n\n"
        f"Дата: {date if date else "Не введено"}\n"
        f"Время: {time if time else "Не введено"}\n"
        f"Количество: {count if count else "Не введено"}\n"
        f"Триггеры: {triggers if triggers else "Не введено"}\n"
        f"Тяжесть: {str(severity) + ' баллов ' if severity else "Не введено"}\n"
        f"Продолжительность: {str(duration) + ' минут ' if duration else "Не введено"}\n"
        f"Комментарий: {comment if comment else "Не введено"}\n"
        f"Симптомы: {symptoms if symptoms else "Не введено"}\n"
        f"Видео: {"✅" if video_tg_id else '❌'}\n"
        f"Место: {"✅" if location else "❌"}"
        f"{action_lines if seizure_id > 0 else ""}"
    )
    return text

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
    location
):
    text = (f"Данные о приступе для профиля <u>{current_profile}</u>:\n\n"
        f"Дата: {date if date else "Не введено"} /update_date{seizure_id}\n\n"
        f"Время: {time if time else "Не введено"} /update_time_{seizure_id}\n\n"
        f"Количество: {count if count else "Не введено"} /update_count_{seizure_id}\n\n"
        f"Триггеры: {triggers if triggers else "Не введено"} /update_triggers_{seizure_id}\n\n"
        f"Тяжесть: {str(severity) + ' баллов ' if severity else "Не введено"} /update_severity_{seizure_id}\n\n"
        f"Продолжительность: {str(duration) + ' минут ' if duration else "Не введено"} /update_duration_{seizure_id}\n\n"
        f"Комментарий: {comment if comment else "Не введено"} /update_comment_{seizure_id}\n\n"
        f"Симптомы: {symptoms if symptoms else "Не введено"} /update_symptoms_{seizure_id}\n\n"
        f"Видео: {"✅" if video_tg_id else '❌'} /update_video_{seizure_id}\n\n"
        f"Место: {"✅" if location else "❌"} /update_location_{seizure_id}")
    return text
