import os
import pandas as pd
import matplotlib.pyplot as plt
import calendar

from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from matplotlib import rcParams

Path("temp_images").mkdir(exist_ok=True)

from database.orm_query import (
    orm_get_seizures_by_profile_ascending,
    orm_get_seizures_by_profile_descending,
    orm_get_seizures_for_a_specific_period
)
from services.redis_cache_data import (
    get_cached_current_profile
)

month_in_russian = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
current_date = datetime.now(timezone.utc)
current_year = datetime.now(timezone.utc).year
current_month = datetime.now(timezone.utc).month
current_month_in_russian = month_in_russian[current_month-1]

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
    return plt.bar(dataX, dataY)

async def get_year_gist(session: AsyncSession, message: Message):
    current_profile = await get_cached_current_profile(session, message.chat.id)
    seizure_data = await orm_get_seizures_for_a_specific_period(
        session,
        int(current_profile.split('|', 1)[0]),
        365
    )
    if seizure_data is None:
        return
    month_arr = range(1, 13)
    count_seizures_by_month = [0] * 12
    for seizure in seizure_data:
        date = datetime.strptime(seizure.date, "%Y-%m-%d")
        print(date)
        if date.month in month_arr:
            count_seizures_by_month[date.month-1] += 1
    make_a_gist(
        title=f"Количество приступов по месяцам в течение {current_year} года ",
        label_x="Месяц",
        label_y="Количество приступов",
        dataX=month_arr,
        dataY=count_seizures_by_month,
        xticks=month_in_russian
    )
    path = 'temp_images/gist_year.png'
    plt.savefig(path)
    file = FSInputFile(path=path)
    await message.answer_photo(
        photo=file,
        caption=f"Гистограмма распределения приступов по месяцам в течении {current_year}"
        f" года для профиля {current_profile.split('|', 1)[1]}",
    )
    os.remove(path)

async def get_month_gist(session: AsyncSession, message: Message):
    days_range = calendar.monthrange(current_year, current_month)[1]
    days_range = [day for day in range(1, days_range + 1)]
    print(days_range)
    count_seizures_by_days = [0] * len(days_range)
    print(count_seizures_by_days)
    print(current_month_in_russian)
    current_profile = await get_cached_current_profile(session, message.chat.id)
    seizures_data = await orm_get_seizures_for_a_specific_period(session, int(current_profile.split('|')[0]), len(days_range))
    if seizures_data is None:
        return
    for seizure in seizures_data:
        date = datetime.strptime(seizure.date, "%Y-%m-%d")
        if date.day in days_range:
            count_seizures_by_days[date.day - 1] += 1
    make_a_gist(
        title=f"Количество приступов за {current_month_in_russian}",
        label_x="День",
        label_y="Количество приступов",
        dataX=days_range,
        dataY=count_seizures_by_days,
        xticks=days_range
    )
    path = 'temp_images/gist_month.png'
    plt.savefig(path)
    file = FSInputFile(path=path)
    await message.answer_photo(
        photo=file,
        caption=f"Гистограмма распределения приступов по дням за {current_month_in_russian}"
        f" для профиля {current_profile.split('|')[1]}",
    )
    os.remove(path)

async def get_total_seizure_count(session: AsyncSession, message: Message):
    current_profile = await get_cached_current_profile(session, message.chat.id)
    seizures_data = await orm_get_seizures_by_profile_ascending(session, int(current_profile.split('|')[0]))
    if seizures_data is None:
        return
    return len(seizures_data)

async def get_day_without_seizures(session: AsyncSession, message: Message):
    current_profile = await get_cached_current_profile(session, message.chat.id)
    seizures_data = await orm_get_seizures_by_profile_descending(session, int(current_profile.split('|')[0]))
    if seizures_data is None:
        return
    last_date_seizure = datetime.strptime(seizures_data[0].date, "%Y-%m-%d")
    print(seizures_data[0].date)
    print(current_date)
    print(last_date_seizure)
    diff = current_date.date() - last_date_seizure.date()
    print(diff)
    print(diff.days)
    return diff.days