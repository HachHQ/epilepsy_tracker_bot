from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.retention import RetentionPurgeStats, purge_expired_data


async def run_retention_purge(session: AsyncSession) -> RetentionPurgeStats:
    return await purge_expired_data(session)
