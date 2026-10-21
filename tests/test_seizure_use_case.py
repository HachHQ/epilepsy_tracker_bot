from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from database.models import Seizure
from database.repositories.seizures import (
    fold_symptom_counts,
    merge_symptom_choices,
    normalize_feature_names,
    normalize_symptom_names,
    replace_seizure_symptoms,
)
from use_cases import seizures as seizure_use_cases
from use_cases.seizures import build_location, build_seizure_date


def test_build_seizure_date_prefers_short_date() -> None:
    assert build_seizure_date({"date_short": "2026-05-27"}) == "2026-05-27"


def test_build_seizure_date_from_parts() -> None:
    assert build_seizure_date({"year": "2026", "month": "05", "day": "27"}) == "2026-05-27"


def test_build_location_combines_geo_and_text() -> None:
    assert build_location({"location": "55.7|37.6", "location_by_message": None}) == "55.7|37.6"
    assert build_location({"location": None, "location_by_message": "home"}) == "home"
    assert build_location({}) is None


@pytest.mark.asyncio
async def test_replace_seizure_symptoms_keeps_unique_names_and_links() -> None:
    seizure = SimpleNamespace(id=3, symptoms="old")
    session = MagicMock()
    session.execute = AsyncMock()
    symptom = SimpleNamespace(id=9)
    with patch(
        "database.repositories.seizures.get_or_create_symptom",
        new=AsyncMock(return_value=symptom),
    ) as create_symptom:
        await replace_seizure_symptoms(session, cast(Seizure, seizure), 1, "Оцепенение, Оцепенение")

    assert seizure.symptoms == "Оцепенение"
    session.execute.assert_awaited()
    create_symptom.assert_awaited_once()
    session.add.assert_called_once()
    link = session.add.call_args.args[0]
    assert link.seizure_id == 3
    assert link.symptom_id == 9


@pytest.mark.asyncio
async def test_replace_seizure_symptoms_clears_an_empty_list() -> None:
    seizure = SimpleNamespace(id=3, symptoms="Оцепенение")
    session = MagicMock()
    session.execute = AsyncMock()
    await replace_seizure_symptoms(session, cast(Seizure, seizure), 1, "")
    assert seizure.symptoms is None
    session.add.assert_not_called()


def test_symptom_names_share_one_spelling_and_rank_by_use() -> None:
    assert normalize_symptom_names("  АУРА , аура,  головная   БОЛЬ ") == ["Аура", "Головная боль"]
    assert fold_symptom_counts([("аура", 1), ("Аура", 2), ("тик", 5)]) == [
        ("Тик", 5),
        ("Аура", 3),
    ]
    choices = merge_symptom_choices(
        ["Оцепенение", "Потеря сознания"],
        ["оцепенение", "тик"],
        ["АУРА"],
    )
    assert choices == ["Оцепенение", "Потеря сознания", "Тик", "Аура"]


def test_normalize_feature_names_accepts_string_or_list() -> None:
    assert normalize_feature_names("stress, sleep") == ["stress", "sleep"]
    assert normalize_feature_names(["stress", " ", "sleep"]) == ["stress", "sleep"]
    assert normalize_feature_names(None) == []


@pytest.mark.asyncio
async def test_list_journal_seizures_delegates_to_repository() -> None:
    fake_seizures = [object(), object()]
    session = AsyncMock()
    with patch(
        "use_cases.seizures.list_profile_seizures",
        new=AsyncMock(return_value=fake_seizures),
    ) as list_mock:
        result = await seizure_use_cases.list_journal_seizures(session, profile_id=4)

    assert result is fake_seizures
    list_mock.assert_awaited_once_with(session, 4, descending=True)


@pytest.mark.asyncio
async def test_delete_seizure_record_invalidates_cache_on_success() -> None:
    with patch(
        "use_cases.seizures.delete_seizure", new=AsyncMock(return_value=True)
    ) as delete_mock, patch(
        "use_cases.seizures.invalidate_seizure_caches", new=AsyncMock()
    ) as invalidate_mock:
        deleted = await seizure_use_cases.delete_seizure_record(
            session=AsyncMock(),
            user_id=10,
            profile_id=3,
            seizure_id=99,
        )

    assert deleted is True
    delete_mock.assert_awaited_once()
    invalidate_mock.assert_awaited_once_with(10, 3)


@pytest.mark.asyncio
async def test_delete_seizure_record_skips_cache_when_not_found() -> None:
    with patch(
        "use_cases.seizures.delete_seizure", new=AsyncMock(return_value=False)
    ), patch(
        "use_cases.seizures.invalidate_seizure_caches", new=AsyncMock()
    ) as invalidate_mock:
        deleted = await seizure_use_cases.delete_seizure_record(
            session=AsyncMock(),
            user_id=10,
            profile_id=3,
            seizure_id=99,
        )

    assert deleted is False
    invalidate_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_seizure_field_invalidates_triggers_only() -> None:
    fake_seizure = object()
    with patch(
        "use_cases.seizures.update_seizure_attribute",
        new=AsyncMock(return_value=fake_seizure),
    ), patch(
        "use_cases.seizures.invalidate_after_seizure_update", new=AsyncMock()
    ) as invalidate_mock:
        result = await seizure_use_cases.update_seizure_field(
            session=AsyncMock(),
            user_id=5,
            profile_id=2,
            seizure_id=7,
            attribute="triggers",
            new_value="stress",
        )

    assert result is fake_seizure
    invalidate_mock.assert_awaited_once_with(5, 2, "triggers")
