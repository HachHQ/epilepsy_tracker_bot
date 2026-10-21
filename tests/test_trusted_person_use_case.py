from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from services.profile_access import profile_ref_for_viewer
from services.profile_ref import ProfileRef
from use_cases import seizures as seizure_use_cases
from use_cases import trusted_persons as trusted_use_cases


def _owned_link():
    return SimpleNamespace(profile_owner_id=3, trusted_person_user_id=8)


@pytest.mark.asyncio
async def test_delete_trusted_person_invalidates_cache() -> None:
    with (
        patch(
            "use_cases.trusted_persons.get_trusted_link_by_id",
            new=AsyncMock(return_value=_owned_link()),
        ),
        patch(
            "use_cases.trusted_persons.get_user_by_chat_id",
            new=AsyncMock(return_value=SimpleNamespace(id=3)),
        ),
        patch(
            "use_cases.trusted_persons.get_user_by_id",
            new=AsyncMock(return_value=SimpleNamespace(telegram_id=100)),
        ),
        patch(
            "use_cases.trusted_persons.delete_trusted_link",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "use_cases.trusted_persons.invalidate_after_trusted_person_mutate",
            new=AsyncMock(),
        ) as invalidate_mock,
        patch(
            "use_cases.trusted_persons.invalidate_current_profile",
            new=AsyncMock(),
        ),
        patch(
            "use_cases.trusted_persons.invalidate_profile_lists",
            new=AsyncMock(),
        ),
    ):
        result = await trusted_use_cases.delete_trusted_person(
            AsyncMock(), 7, owner_chat_id=42
        )

    assert result.deleted is True
    invalidate_mock.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_delete_trusted_person_rejects_foreign_link() -> None:
    with (
        patch(
            "use_cases.trusted_persons.get_trusted_link_by_id",
            new=AsyncMock(return_value=_owned_link()),
        ),
        patch(
            "use_cases.trusted_persons.get_user_by_chat_id",
            new=AsyncMock(return_value=SimpleNamespace(id=99)),
        ),
        patch(
            "use_cases.trusted_persons.delete_trusted_link",
            new=AsyncMock(),
        ) as delete_mock,
    ):
        result = await trusted_use_cases.delete_trusted_person(
            AsyncMock(), 7, owner_chat_id=5
        )

    assert result.deleted is False
    delete_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_toggle_edit_permission_returns_not_found() -> None:
    with patch(
        "use_cases.trusted_persons.get_trusted_link_by_id",
        new=AsyncMock(return_value=None),
    ):
        result = await trusted_use_cases.toggle_edit_permission(
            AsyncMock(), 99, owner_chat_id=1
        )

    assert result.updated is False
    assert result.link is None


@pytest.mark.asyncio
async def test_create_trusted_request_rejects_foreign_profile() -> None:
    with patch(
        "use_cases.trusted_persons.get_active_profile_by_id",
        new=AsyncMock(return_value=SimpleNamespace(user_id=5)),
    ), patch(
        "use_cases.trusted_persons.create_trusted_person_request",
        new=AsyncMock(),
    ) as create_mock:
        result = await trusted_use_cases.create_trusted_request(
            AsyncMock(),
            sender_id=9,
            recipient_id=2,
            profile_id=4,
        )

    assert result.reason == "not_owner"
    create_mock.assert_not_awaited()


def test_guest_with_read_only_link_cannot_edit() -> None:
    access = profile_ref_for_viewer(
        8, 3, 4, "Дневник", link_can_read=True, link_can_edit=False
    )
    assert access is not None
    assert access.is_owner is False
    assert access.can_edit is False


def test_missing_link_denies_guest() -> None:
    assert profile_ref_for_viewer(
        8, 3, 4, "Дневник", link_can_read=None, link_can_edit=None
    ) is None


def test_owner_keeps_full_access() -> None:
    access = profile_ref_for_viewer(
        3, 3, 4, "Дневник", link_can_read=None, link_can_edit=None
    )
    assert access is not None
    assert access.is_owner is True
    assert access.can_edit is True


@pytest.mark.asyncio
async def test_read_only_profile_does_not_create_seizure() -> None:
    with patch(
        "use_cases.seizures.create_seizure",
        new=AsyncMock(),
    ) as create_mock:
        result = await seizure_use_cases.create_seizure_from_state(
            AsyncMock(),
            user_id=1,
            profile=ProfileRef(id=4, name="Дневник", can_edit=False, is_owner=False),
            creator_login="guest",
            state_data={},
        )

    assert result is None
    create_mock.assert_not_awaited()


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
