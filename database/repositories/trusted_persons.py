import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from database.models import (
    Profile,
    RequestStatus,
    TrustedPersonProfiles,
    TrustedPersonRequest,
    User,
)


async def list_trusted_profiles_for_guest(
    session: AsyncSession,
    chat_id: int,
) -> list[dict]:
    result = await session.execute(
        select(Profile)
        .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
        .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
        .where(User.telegram_id == chat_id, Profile.deleted_at.is_(None))
    )
    return [profile.to_dict() for profile in result.scalars().all()]


async def list_trusted_persons_for_owner(
    session: AsyncSession,
    owner_chat_id: int,
) -> list[dict]:
    owner_alias = aliased(User)
    result = await session.execute(
        select(User, TrustedPersonProfiles, Profile, owner_alias)
        .join(TrustedPersonProfiles, User.id == TrustedPersonProfiles.trusted_person_user_id)
        .join(owner_alias, TrustedPersonProfiles.profile_owner_id == owner_alias.id)
        .join(Profile, TrustedPersonProfiles.profile_id == Profile.id)
        .where(owner_alias.telegram_id == owner_chat_id)
    )
    trusted_data = []
    for trusted_user, trusted_profile, profile, owner in result.all():
        trusted_data.append(
            {
                "trusted_user": trusted_user.to_dict(),
                "profile_owner": owner.to_dict(),
                "profile": profile.to_dict(),
                "permissions": {
                    "id": trusted_profile.id,
                    "can_read": trusted_profile.can_read,
                    "can_edit": trusted_profile.can_edit,
                    "created_at": trusted_profile.created_at,
                    "get_notification": trusted_profile.get_notification,
                },
            }
        )
    return trusted_data


async def can_trusted_person_read(
    session: AsyncSession,
    trusted_person_id: int,
    profile_owner_id: int,
    profile_id: int,
) -> bool:
    link = await session.scalar(
        select(TrustedPersonProfiles).where(
            TrustedPersonProfiles.trusted_person_user_id == int(trusted_person_id),
            TrustedPersonProfiles.profile_owner_id == int(profile_owner_id),
            TrustedPersonProfiles.profile_id == int(profile_id),
        )
    )
    return bool(link and link.can_read)


async def can_trusted_person_edit(
    session: AsyncSession,
    trusted_person_id: int,
    profile_owner_id: int,
    profile_id: int,
) -> bool:
    link = await session.scalar(
        select(TrustedPersonProfiles).where(
            TrustedPersonProfiles.trusted_person_user_id == int(trusted_person_id),
            TrustedPersonProfiles.profile_owner_id == int(profile_owner_id),
            TrustedPersonProfiles.profile_id == int(profile_id),
        )
    )
    return bool(link and link.can_edit)


async def get_trusted_link_by_id(
    session: AsyncSession,
    tpp_id: int,
) -> TrustedPersonProfiles | None:
    return await session.scalar(
        select(TrustedPersonProfiles).where(TrustedPersonProfiles.id == int(tpp_id))
    )


async def delete_trusted_link(session: AsyncSession, tpp_id: int) -> bool:
    result = await session.execute(
        delete(TrustedPersonProfiles).where(TrustedPersonProfiles.id == int(tpp_id))
    )
    return result.rowcount > 0


async def toggle_trusted_edit_permission(
    session: AsyncSession,
    tpp_id: int,
) -> TrustedPersonProfiles | None:
    link = await get_trusted_link_by_id(session, tpp_id)
    if not link:
        return None
    link.can_edit = not link.can_edit
    await session.flush()
    return link


async def toggle_trusted_notify_permission(
    session: AsyncSession,
    tpp_id: int,
) -> TrustedPersonProfiles | None:
    link = await get_trusted_link_by_id(session, tpp_id)
    if not link:
        return None
    link.get_notification = not link.get_notification
    await session.flush()
    return link


async def get_existing_trusted_link(
    session: AsyncSession,
    *,
    trusted_person_user_id: int,
    profile_owner_id: int,
    profile_id: int,
) -> TrustedPersonProfiles | None:
    return await session.scalar(
        select(TrustedPersonProfiles).where(
            TrustedPersonProfiles.trusted_person_user_id == int(trusted_person_user_id),
            TrustedPersonProfiles.profile_owner_id == int(profile_owner_id),
            TrustedPersonProfiles.profile_id == int(profile_id),
        )
    )


async def create_trusted_person_request(
    session: AsyncSession,
    *,
    sender_id: int,
    recipient_id: int,
    profile_id: int,
    request_id: str | None = None,
) -> TrustedPersonRequest:
    short_uuid = request_id or str(uuid.uuid4())[:16]
    request = TrustedPersonRequest(
        id=short_uuid,
        sender_id=int(sender_id),
        recepient_id=int(recipient_id),
        transmitted_profile_id=int(profile_id),
        status=RequestStatus.PENDING,
    )
    session.add(request)
    await session.flush()
    return request


async def get_trusted_person_request(
    session: AsyncSession,
    *,
    request_id: str,
    sender_id: int,
    recipient_id: int,
) -> TrustedPersonRequest | None:
    return await session.scalar(
        select(TrustedPersonRequest).where(
            TrustedPersonRequest.id == request_id,
            TrustedPersonRequest.sender_id == int(sender_id),
            TrustedPersonRequest.recepient_id == int(recipient_id),
        )
    )


async def accept_trusted_person_request(
    session: AsyncSession,
    request: TrustedPersonRequest,
) -> TrustedPersonProfiles:
    request.status = RequestStatus.ACCEPTED
    link = TrustedPersonProfiles(
        trusted_person_user_id=request.recepient_id,
        profile_owner_id=request.sender_id,
        profile_id=request.transmitted_profile_id,
    )
    session.add(link)
    await session.flush()
    return link


async def reject_trusted_person_request(
    session: AsyncSession,
    request: TrustedPersonRequest,
) -> None:
    request.status = RequestStatus.REJECTED
    await session.flush()


async def expire_trusted_person_request(
    session: AsyncSession,
    request: TrustedPersonRequest,
) -> None:
    request.status = RequestStatus.EXPIRED
    await session.flush()
