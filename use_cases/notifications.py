from dataclasses import dataclass
from datetime import time

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserNotifications
from database.repositories.notifications import (
    create_notification,
    delete_notification,
    get_notification_by_id,
    list_user_notifications,
    update_notification_attribute,
)


@dataclass(frozen=True)
class CreateNotificationResult:
    notification: UserNotifications


@dataclass(frozen=True)
class UpdateNotificationResult:
    updated: bool
    notification: UserNotifications | None = None


@dataclass(frozen=True)
class DeleteNotificationResult:
    deleted: bool


async def list_notifications(session: AsyncSession, user_id: int) -> list[UserNotifications]:
    return await list_user_notifications(session, user_id)


async def get_notification(
    session: AsyncSession,
    user_id: int,
    notification_id: int,
) -> UserNotifications | None:
    return await get_notification_by_id(session, user_id, notification_id)


async def create_notification_from_form(
    session: AsyncSession,
    *,
    user_id: int,
    notify_time: time,
    note: str,
    pattern: str,
) -> CreateNotificationResult:
    notification = await create_notification(
        session,
        user_id=user_id,
        notify_time=notify_time,
        note=note,
        pattern=pattern,
    )
    return CreateNotificationResult(notification=notification)


async def update_notification_field(
    session: AsyncSession,
    *,
    user_id: int,
    notification_id: int,
    attribute: str,
    new_value,
) -> UpdateNotificationResult:
    notification = await update_notification_attribute(
        session,
        user_id,
        notification_id,
        attribute,
        new_value,
    )
    return UpdateNotificationResult(updated=notification is not None, notification=notification)


async def delete_user_notification(
    session: AsyncSession,
    *,
    user_id: int,
    notification_id: int,
) -> DeleteNotificationResult:
    deleted = await delete_notification(session, user_id, notification_id)
    return DeleteNotificationResult(deleted=deleted)
