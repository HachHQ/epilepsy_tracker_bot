from datetime import time

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserNotifications


async def list_user_notifications(
    session: AsyncSession,
    user_id: int,
) -> list[UserNotifications]:
    result = await session.execute(
        select(UserNotifications).where(UserNotifications.user_id == int(user_id))
    )
    return list(result.scalars().all())


async def get_notification_by_id(
    session: AsyncSession,
    user_id: int,
    notification_id: int,
) -> UserNotifications | None:
    return await session.scalar(
        select(UserNotifications).where(
            UserNotifications.user_id == int(user_id),
            UserNotifications.id == int(notification_id),
        )
    )


async def create_notification(
    session: AsyncSession,
    *,
    user_id: int,
    notify_time: time,
    note: str,
    pattern: str,
) -> UserNotifications:
    notification = UserNotifications(
        user_id=int(user_id),
        notify_time=notify_time,
        note=note,
        pattern=pattern,
    )
    session.add(notification)
    await session.flush()
    return notification


async def update_notification_attribute(
    session: AsyncSession,
    user_id: int,
    notification_id: int,
    attribute: str,
    new_value,
) -> UserNotifications | None:
    notification = await get_notification_by_id(session, user_id, notification_id)
    if not notification:
        return None
    if not hasattr(notification, attribute):
        raise ValueError(f"Атрибут '{attribute}' не существует в модели UserNotifications.")
    setattr(notification, attribute, new_value)
    await session.flush()
    return notification


async def delete_notification(
    session: AsyncSession,
    user_id: int,
    notification_id: int,
) -> bool:
    result = await session.execute(
        delete(UserNotifications).where(
            UserNotifications.id == int(notification_id),
            UserNotifications.user_id == int(user_id),
        )
    )
    return result.rowcount > 0
