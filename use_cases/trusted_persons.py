from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RequestStatus, TrustedPersonProfiles, TrustedPersonRequest, User
from database.redis_query import set_redis_cached_profiles_list
from database.repositories.trusted_persons import (
    accept_trusted_person_request,
    can_trusted_person_edit,
    can_trusted_person_read,
    create_trusted_person_request,
    delete_trusted_link,
    expire_trusted_person_request,
    get_existing_trusted_link,
    get_trusted_person_request,
    list_trusted_persons_for_owner,
    list_trusted_profiles_for_guest,
    reject_trusted_person_request,
    toggle_trusted_edit_permission,
    toggle_trusted_notify_permission,
)
from database.repositories.users import get_user_by_login
from services.cache_invalidation import invalidate_after_trusted_person_mutate


@dataclass(frozen=True)
class DeleteTrustedPersonResult:
    deleted: bool


@dataclass(frozen=True)
class TogglePermissionResult:
    updated: bool
    link: TrustedPersonProfiles | None = None


@dataclass(frozen=True)
class CreateTrustedRequestResult:
    request: TrustedPersonRequest
    request_uuid: str


@dataclass(frozen=True)
class AcceptTrustedRequestResult:
    accepted: bool
    link: TrustedPersonProfiles | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ProcessTrustedRequestResult:
    processed: bool
    reason: str | None = None


async def list_guest_trusted_profiles(session: AsyncSession, chat_id: int) -> list[dict]:
    return await list_trusted_profiles_for_guest(session, chat_id)


async def list_owner_trusted_persons(session: AsyncSession, owner_chat_id: int) -> list[dict]:
    return await list_trusted_persons_for_owner(session, owner_chat_id)


async def find_user_by_login(session: AsyncSession, login: str) -> User | None:
    return await get_user_by_login(session, login)


async def user_can_read_profile(
    session: AsyncSession,
    *,
    trusted_person_id: int,
    profile_owner_id: int,
    profile_id: int,
) -> bool:
    return await can_trusted_person_read(session, trusted_person_id, profile_owner_id, profile_id)


async def user_can_edit_profile(
    session: AsyncSession,
    *,
    trusted_person_id: int,
    profile_owner_id: int,
    profile_id: int,
) -> bool:
    return await can_trusted_person_edit(session, trusted_person_id, profile_owner_id, profile_id)


async def delete_trusted_person(
    session: AsyncSession,
    tpp_id: int,
    *,
    owner_chat_id: int | None = None,
) -> DeleteTrustedPersonResult:
    deleted = await delete_trusted_link(session, tpp_id)
    if deleted and owner_chat_id is not None:
        await invalidate_after_trusted_person_mutate(owner_chat_id)
    return DeleteTrustedPersonResult(deleted=deleted)


async def toggle_edit_permission(
    session: AsyncSession,
    tpp_id: int,
    *,
    owner_chat_id: int | None = None,
) -> TogglePermissionResult:
    link = await toggle_trusted_edit_permission(session, tpp_id)
    if link is not None and owner_chat_id is not None:
        await invalidate_after_trusted_person_mutate(owner_chat_id)
    return TogglePermissionResult(updated=link is not None, link=link)


async def toggle_notify_permission(
    session: AsyncSession,
    tpp_id: int,
    *,
    owner_chat_id: int | None = None,
) -> TogglePermissionResult:
    link = await toggle_trusted_notify_permission(session, tpp_id)
    if link is not None and owner_chat_id is not None:
        await invalidate_after_trusted_person_mutate(owner_chat_id)
    return TogglePermissionResult(updated=link is not None, link=link)


async def trusted_link_exists(
    session: AsyncSession,
    *,
    trusted_person_user_id: int,
    profile_owner_id: int,
    profile_id: int,
) -> bool:
    link = await get_existing_trusted_link(
        session,
        trusted_person_user_id=trusted_person_user_id,
        profile_owner_id=profile_owner_id,
        profile_id=profile_id,
    )
    return link is not None


async def create_trusted_request(
    session: AsyncSession,
    *,
    sender_id: int,
    recipient_id: int,
    profile_id: int,
) -> CreateTrustedRequestResult:
    request = await create_trusted_person_request(
        session,
        sender_id=sender_id,
        recipient_id=recipient_id,
        profile_id=profile_id,
    )
    return CreateTrustedRequestResult(request=request, request_uuid=request.id)


async def accept_trusted_request(
    session: AsyncSession,
    *,
    request_id: str,
    sender_id: int,
    recipient_id: int,
    recipient_chat_id: int | None = None,
    now: datetime | None = None,
) -> AcceptTrustedRequestResult:
    from datetime import UTC
    from datetime import datetime as dt

    request = await get_trusted_person_request(
        session,
        request_id=request_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
    )
    if not request:
        return AcceptTrustedRequestResult(accepted=False, reason="not_found")

    if request.status != RequestStatus.PENDING:
        return AcceptTrustedRequestResult(accepted=False, reason="already_processed")

    current_time = now or dt.now(UTC)
    if current_time > request.expires_at:
        await expire_trusted_person_request(session, request)
        return AcceptTrustedRequestResult(accepted=False, reason="expired")

    link = await accept_trusted_person_request(session, request)
    if recipient_chat_id is not None:
        profiles = await list_trusted_profiles_for_guest(session, recipient_chat_id)
        await set_redis_cached_profiles_list(recipient_chat_id, "trusted", profiles)
        await invalidate_after_trusted_person_mutate(recipient_chat_id)
    return AcceptTrustedRequestResult(accepted=True, link=link)


async def reject_trusted_request(
    session: AsyncSession,
    *,
    request_id: str,
    sender_id: int,
    recipient_id: int,
) -> ProcessTrustedRequestResult:
    request = await get_trusted_person_request(
        session,
        request_id=request_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
    )
    if not request:
        return ProcessTrustedRequestResult(processed=False, reason="not_found")

    if request.status != RequestStatus.PENDING:
        return ProcessTrustedRequestResult(processed=False, reason="already_processed")

    await reject_trusted_person_request(session, request)
    return ProcessTrustedRequestResult(processed=True)
