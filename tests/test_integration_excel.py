import os

import pandas as pd
import pytest

from database.repositories.seizures import create_seizure
from i18n import set_locale, t
from use_cases import import_export as import_export_use_cases

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_build_seizures_excel_contains_seizure_row(db_session, test_user) -> None:
    await create_seizure(
        db_session,
        profile_id=test_user["profile"].id,
        date="2026-05-27",
        time="09:15",
        severity="2",
        duration=90,
        comment="excel export test",
        count=1,
        video_tg_id=None,
        trigger_names=["stress"],
        symptom_names=["aura"],
        location="home",
        creator_login=test_user["user"].login,
        type_of_seizure="focal",
    )
    await db_session.flush()

    path = await import_export_use_cases.export_profile_seizures_excel(
        db_session, test_user["profile"].id
    )
    try:
        set_locale("ru")
        df = pd.read_excel(path)
        assert len(df) == 1
        assert df.iloc[0][t("excel.column_date")] == "2026-05-27"
        assert df.iloc[0][t("excel.column_comment")] == "excel export test"
        assert "stress" in str(df.iloc[0][t("excel.column_triggers")]).lower()
        assert "aura" in str(df.iloc[0][t("excel.column_symptoms")]).lower()
    finally:
        if os.path.exists(path):
            os.remove(path)
