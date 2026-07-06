from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from services.to_excel import EXPECTED_COLUMNS
from use_cases import import_export as import_export_use_cases


@pytest.mark.asyncio
async def test_export_profile_seizures_excel_delegates_to_repository() -> None:
    rows = [{"date": "2026-01-01", "time": "10:00", "severity": "1", "duration": 60,
             "comment": None, "type_of_seizure": None, "location": None,
             "triggers": "", "symptoms": ""}]
    with (
        patch(
            "use_cases.import_export.list_seizure_export_rows",
            new=AsyncMock(return_value=rows),
        ) as repo_mock,
        patch(
            "use_cases.import_export.write_seizures_excel",
            return_value="temp_tables/report.xlsx",
        ) as write_mock,
    ):
        path = await import_export_use_cases.export_profile_seizures_excel(AsyncMock(), 5)

    assert path == "temp_tables/report.xlsx"
    repo_mock.assert_awaited_once()
    write_mock.assert_called_once_with(rows)


@pytest.mark.asyncio
async def test_import_seizures_invalidates_cache_on_success() -> None:
    with (
        patch("use_cases.import_export.pd.read_excel") as read_mock,
        patch("use_cases.import_export.validate_row", return_value=True),
        patch("use_cases.import_export.create_seizure", new=AsyncMock()),
        patch(
            "use_cases.import_export.invalidate_seizure_caches",
            new=AsyncMock(),
        ) as invalidate_mock,
    ):
        read_mock.return_value.columns = EXPECTED_COLUMNS
        row = pd.Series(
            {
                "date": "01.01.2026",
                "time": "10:00",
                "duration": 60,
                "severity": None,
                "comment": None,
                "type_of_seizure": None,
                "location": None,
                "triggers": None,
                "symptoms": None,
            }
        )
        read_mock.return_value.iterrows.return_value = [(0, row)]
        result = await import_export_use_cases.import_seizures_from_excel(
            AsyncMock(),
            file_path="import.xlsx",
            profile_id=3,
            login="user",
            user_id=10,
        )

    assert result.success_count == 1
    invalidate_mock.assert_awaited_once_with(10, 3)
