def get_formatted_seizure_info(
    callback,
    current_profile,
    date = 'Не заполнено',
    time_of_day = 'Не заполнено',
    count = 'Не заполнено',
    triggers = 'Не заполнено',
    severity = 'Не заполнено',
    duration = 'Не заполнено',
    comment = 'Не заполнено',
    symptoms = 'Не заполнено',
    video_tg_id = 'Не заполнено',
    location = 'Не заполнено'
):
    text = (f"Введенные данные о приступе для профиля <u>{current_profile}</u>:\n"
        f"Дата: {date}\n"
        f"Время: {time_of_day}\n"
        f"Количество: {count}\n"
        f"Триггеры: {triggers}\n"
        f"Тяжесть: {severity} баллов\n"
        f"Продолжительность: {duration} минут\n"
        f"Комментарий: {comment}\n"
        f"Симптомы: {symptoms}\n"
        f"Видео: {"✅" if video_tg_id != "Не заполнено" else video_tg_id}\n"
        f"Место: {location}")
    return text

def get_formatted_seizure_edit(
    current_profile,
    seizure_id,
    date = 'Не заполнено',
    time_of_day = 'Не заполнено',
    count = 'Не заполнено',
    triggers = 'Не заполнено',
    severity = 'Не заполнено',
    duration = 'Не заполнено',
    comment = 'Не заполнено',
    symptoms = 'Не заполнено',
    video_tg_id = 'Не заполнено',
    location = 'Не заполнено'
):
    text = (f"Введенные данные о приступе для профиля <u>{current_profile}</u>:\n"
        f"Дата: {date} /edit_date{seizure_id}\n"
        f"Время: {time_of_day} /edit_time{seizure_id}\n"
        f"Количество: {count} /edit_count{seizure_id}\n"
        f"Триггеры: {triggers} /edit_triggers{seizure_id}\n"
        f"Тяжесть: {severity} /edit_severity{seizure_id}\n"
        f"Продолжительность: {duration} минут /edit_duration{seizure_id}\n"
        f"Комментарий: {comment} /edit_comment{seizure_id}\n"
        f"Симптомы: {symptoms} /edit_symptoms{seizure_id}\n"
        f"Видео: {"✅" if video_tg_id != "Не заполнено" else video_tg_id} /edit_video{seizure_id}\n"
        f"Место: {location} /edit_location{seizure_id}")
    return text