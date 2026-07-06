from dataclasses import dataclass

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.import_export import list_seizure_export_rows
from database.repositories.seizures import create_seizure
from i18n import t
from services.cache_invalidation import invalidate_seizure_caches
from services.to_excel import (
    EXPECTED_COLUMNS,
    parse_excel_time,
    validate_row,
    write_seizures_excel,
)


@dataclass(frozen=True)
class ImportSeizuresResult:
    success_count: int
    failed_rows: list[dict]


async def export_profile_seizures_excel(session: AsyncSession, profile_id: int) -> str:
    rows = await list_seizure_export_rows(session, profile_id)
    return write_seizures_excel(rows)


async def import_seizures_from_excel(
    session: AsyncSession,
    *,
    file_path: str,
    profile_id: int,
    login: str,
    user_id: int,
) -> ImportSeizuresResult:
    df = pd.read_excel(file_path)
    if set(EXPECTED_COLUMNS) - set(df.columns):
        raise ValueError(t("excel.missing_columns"))

    failed_rows: list[dict] = []
    success_count = 0
    for _index, row in df.iterrows():
        if not validate_row(row):
            failed_rows.append(row.to_dict())
            continue
        try:
            raw_date = pd.to_datetime(row["date"], dayfirst=True)
            raw_time = parse_excel_time(row["time"])
            await create_seizure(
                session,
                profile_id=profile_id,
                date=raw_date.strftime("%Y-%m-%d"),
                time=raw_time.strftime("%H:%M") if raw_time else None,
                severity=str(row.get("severity")) if pd.notna(row.get("severity")) else None,
                duration=int(row["duration"]) if pd.notna(row["duration"]) else None,
                comment=row.get("comment") if pd.notna(row.get("comment")) else None,
                count=None,
                video_tg_id=None,
                trigger_names=row.get("triggers") if pd.notna(row.get("triggers")) else None,
                symptom_names=row.get("symptoms") if pd.notna(row.get("symptoms")) else None,
                location=row.get("location") if pd.notna(row.get("location")) else None,
                creator_login=login,
                type_of_seizure=row.get("type_of_seizure")
                if pd.notna(row.get("type_of_seizure"))
                else None,
            )
            success_count += 1
        except Exception:
            await session.rollback()
            failed_rows.append(row.to_dict())

    if success_count:
        await invalidate_seizure_caches(user_id, profile_id)

    return ImportSeizuresResult(success_count=success_count, failed_rows=failed_rows)
