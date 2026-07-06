import importlib.util

import pytest


def test_orm_query_module_removed() -> None:
    spec = importlib.util.find_spec("database.orm_query")
    assert spec is None


def test_handlers_do_not_import_orm_query() -> None:
    import pathlib

    handlers_dir = pathlib.Path("handlers")
    for path in handlers_dir.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert "database.orm_query" not in content, path.as_posix()


@pytest.mark.asyncio
async def test_analytics_use_case_delegates_to_repository() -> None:
    from unittest.mock import AsyncMock, patch

    from use_cases import analytics as analytics_use_cases

    fake_stats = {"top_symptoms": [], "top_triggers": [], "top_types": []}
    with patch(
        "use_cases.analytics.get_top_seizure_features",
        new=AsyncMock(return_value=fake_stats),
    ) as repo_mock:
        result = await analytics_use_cases.get_profile_feature_stats(AsyncMock(), profile_id=3)

    assert result is fake_stats
    repo_mock.assert_awaited_once()
