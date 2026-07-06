from datetime import time
from unittest.mock import AsyncMock, patch

import pytest

from use_cases import notifications as notification_use_cases


@pytest.mark.asyncio
async def test_create_notification_from_form_delegates_to_repository() -> None:
    fake_notification = object()
    with patch(
        "use_cases.notifications.create_notification",
        new=AsyncMock(return_value=fake_notification),
    ) as create_mock:
        result = await notification_use_cases.create_notification_from_form(
            session=AsyncMock(),
            user_id=5,
            notify_time=time(12, 0),
            note="Take meds",
            pattern="daily",
        )

    assert result.notification is fake_notification
    create_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_notification_field_returns_not_found() -> None:
    with patch(
        "use_cases.notifications.update_notification_attribute",
        new=AsyncMock(return_value=None),
    ):
        result = await notification_use_cases.update_notification_field(
            session=AsyncMock(),
            user_id=1,
            notification_id=99,
            attribute="note",
            new_value="Updated",
        )

    assert result.updated is False
    assert result.notification is None


@pytest.mark.asyncio
async def test_delete_user_notification_returns_deleted_flag() -> None:
    with patch(
        "use_cases.notifications.delete_notification",
        new=AsyncMock(return_value=True),
    ):
        result = await notification_use_cases.delete_user_notification(
            session=AsyncMock(),
            user_id=1,
            notification_id=3,
        )

    assert result.deleted is True
