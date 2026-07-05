from unittest.mock import AsyncMock, patch

import pytest

from database.repositories.seizures import normalize_feature_names
from use_cases import seizures as seizure_use_cases
from use_cases.seizures import build_location, build_seizure_date, parse_current_profile


def test_parse_current_profile() -> None:
    assert parse_current_profile("12|Основной") == (12, "Основной")


def test_build_seizure_date_prefers_short_date() -> None:
    assert build_seizure_date({"date_short": "2026-05-27"}) == "2026-05-27"


def test_build_seizure_date_from_parts() -> None:
    assert build_seizure_date({"year": "2026", "month": "05", "day": "27"}) == "2026-05-27"


def test_build_location_combines_geo_and_text() -> None:
    assert build_location({"location": "55.7|37.6", "location_by_message": None}) == "55.7|37.6"
    assert build_location({"location": None, "location_by_message": "home"}) == "home"
    assert build_location({}) is None


def test_normalize_feature_names_accepts_string_or_list() -> None:
    assert normalize_feature_names("stress, sleep") == ["stress", "sleep"]
    assert normalize_feature_names(["stress", " ", "sleep"]) == ["stress", "sleep"]
    assert normalize_feature_names(None) == []


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
