from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import USER_DATA_RETENTION_DAYS, retention_deadline
from database.models import (
    Profile,
    TrustedPersonProfiles,
    TrustedPersonRequest,
    User,
    UserNotifications,
)
from database.repositories.profiles import soft_delete_profile


async def get_user_by_chat_id(
    session: AsyncSession,
    chat_id: int,
    *,
    include_deleted: bool = False,
) -> User | None:
    query = select(User).where(User.telegram_id == chat_id)
    if not include_deleted:
        query = query.where(User.deleted_at.is_(None))
    result = await session.execute(query)
    return result.scalars().first()


async def get_deleted_user_by_chat_id(session: AsyncSession, chat_id: int) -> User | None:
    return await session.scalar(
        select(User).where(
            User.telegram_id == chat_id,
            User.deleted_at.is_not(None),
        )
    )


async def get_user_by_login(session: AsyncSession, login: str) -> User | None:
    result = await session.execute(
        select(User).where(User.login == login, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def create_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    telegram_username: str | None,
    telegram_fullname: str | None,
    name: str,
    login: str,
    timezone: str,
    keyword_hash: str,
) -> User:
    user = User(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        telegram_fullname=telegram_fullname,
        name=name,
        login=login,
        timezone=timezone,
        keyword_hash=keyword_hash,
    )
    session.add(user)
    await session.flush()
    return user


async def soft_delete_user(session: AsyncSession, user_id: int) -> bool:
    user = await session.scalar(
        select(User).where(User.id == int(user_id), User.deleted_at.is_(None))
    )
    if not user:
        return False

    now = datetime.now(UTC)
    deadline = retention_deadline(days=USER_DATA_RETENTION_DAYS, from_time=now)

    active_profiles = await session.scalars(
        select(Profile.id).where(
            Profile.user_id == user.id,
            Profile.deleted_at.is_(None),
        )
    )
    for profile_id in active_profiles.all():
        await soft_delete_profile(session, profile_id)

    await session.execute(
        delete(UserNotifications).where(UserNotifications.user_id == user.id)
    )
    await session.execute(
        delete(TrustedPersonProfiles).where(
            (TrustedPersonProfiles.trusted_person_user_id == user.id)
            | (TrustedPersonProfiles.profile_owner_id == user.id)
        )
    )
    await session.execute(
        delete(TrustedPersonRequest).where(
            (TrustedPersonRequest.sender_id == user.id)
            | (TrustedPersonRequest.recepient_id == user.id)
        )
    )

    user.deleted_at = now
    user.data_retention_until = deadline
    user.keyword_hash = None
    user.current_profile = None
    user.name = "Удалённый аккаунт"
    user.telegram_username = None
    user.telegram_fullname = None

    await session.flush()
    return True


async def restore_user(
    session: AsyncSession,
    chat_id: int,
    *,
    telegram_username: str | None = None,
    telegram_fullname: str | None = None,
    keyword_hash: str | None = None,
) -> User | None:
    user = await get_deleted_user_by_chat_id(session, chat_id)
    if not user:
        return None

    now = datetime.now(UTC)
    if user.data_retention_until and user.data_retention_until < now:
        return None

    user.deleted_at = None
    user.data_retention_until = None
    if telegram_username is not None:
        user.telegram_username = telegram_username
    if telegram_fullname is not None:
        user.telegram_fullname = telegram_fullname
        user.name = telegram_fullname[:25]
    if keyword_hash is not None:
        user.keyword_hash = keyword_hash

    await session.flush()
    return user
