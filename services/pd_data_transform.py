import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database.orm_query import orm_get_seizures_by_profile_ascending
from database.redis_query import get_redis_cached_current_profile

def format_orm_data_obj_to_dict(orm_table):
    data = [atr.__dict__ for atr in orm_table]
    for item in data:
        item.pop('_sa_instance_state', None)
    return data

async def pd_get_min_max_year_in_seizures(session: AsyncSession, chat_id: int):
    current_profile = await get_redis_cached_current_profile(chat_id)
    if not current_profile:
        return None
    seizures = await orm_get_seizures_by_profile_ascending(session, int(current_profile.split('|', 1)[0]))
    uniq_years = []
    try:
        years = [int(datetime.strptime(seizure.date, '%Y-%m-%d').year) for seizure in seizures if seizure.date]
        for year in years:
            if year not in uniq_years:
                uniq_years.append(year)

    except ValueError:
        return "Ошибка: Неверный формат даты."
    if not years:
        return "Нет данных"

    min_year = min(years)
    max_year = max(years)
    print(sorted(uniq_years))
    result = f"{min_year}-{max_year}"
    print(result)
    return sorted(uniq_years)
