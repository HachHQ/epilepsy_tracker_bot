from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.analytics import get_avg_duration_by_month, get_top_seizure_features


async def get_profile_feature_stats(session: AsyncSession, profile_id: int) -> dict:
    return await get_top_seizure_features(session, profile_id)


async def get_monthly_avg_duration(session: AsyncSession, profile_id: int, year: int):
    return await get_avg_duration_by_month(session, profile_id, year)
