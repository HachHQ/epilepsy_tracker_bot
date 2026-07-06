from unittest.mock import AsyncMock, patch

import pytest

from use_cases import trusted_persons as trusted_use_cases


@pytest.mark.asyncio
async def test_delete_trusted_person_returns_deleted_flag() -> None:
    with patch(
        "use_cases.trusted_persons.delete_trusted_link",
        new=AsyncMock(return_value=True),
    ):
        result = await trusted_use_cases.delete_trusted_person(AsyncMock(), 7)

    assert result.deleted is True


@pytest.mark.asyncio
async def test_toggle_edit_permission_returns_not_found() -> None:
    with patch(
        "use_cases.trusted_persons.toggle_trusted_edit_permission",
        new=AsyncMock(return_value=None),
    ):
        result = await trusted_use_cases.toggle_edit_permission(AsyncMock(), 99)

    assert result.updated is False
    assert result.link is None


@pytest.mark.asyncio
async def test_accept_trusted_request_returns_not_found() -> None:
    with patch(
        "use_cases.trusted_persons.get_trusted_person_request",
        new=AsyncMock(return_value=None),
    ):
        result = await trusted_use_cases.accept_trusted_request(
            AsyncMock(),
            request_id="abc",
            sender_id=1,
            recipient_id=2,
        )

    assert result.accepted is False
    assert result.reason == "not_found"
