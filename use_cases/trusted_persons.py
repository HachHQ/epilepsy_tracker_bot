from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RequestStatus, TrustedPersonProfiles, TrustedPersonRequest, User
from database.repositories.profiles import get_active_profile_by_id
from database.repositories.trusted_persons import (
    accept_trusted_person_request,
    can_trusted_person_edit,
    can_trusted_person_read,
    create_trusted_person_request,
    delete_trusted_link,
    expire_trusted_person_request,
    get_existing_trusted_link,
    get_trusted_link_by_id,
    get_trusted_person_request,
    list_trusted_persons_for_owner,
    list_trusted_profiles_for_guest,
    reject_trusted_person_request,
    toggle_trusted_edit_permission,
    toggle_trusted_notify_permission,
)
from database.repositories.users import get_user_by_chat_id, get_user_by_id, get_user_by_login
from services.cache_invalidation import (
    invalidate_after_trusted_person_mutate,
    invalidate_current_profile,
    invalidate_profile_lists,
)
from services.redis_cache_data import remember_profiles_list


@dataclass(frozen=True)
class DeleteTrustedPersonResult:
    deleted: bool


@dataclass(frozen=True)
class TogglePermissionResult:
    updated: bool
    link: TrustedPersonProfiles | None = None


@dataclass(frozen=True)
class CreateTrustedRequestResult:
    request: TrustedPersonRequest | None = None
    request_uuid: str | None = None
    reason: str | None = None


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


async def _owner_link(session: AsyncSession, tpp_id: int, owner_chat_id: int | None):
    link = await get_trusted_link_by_id(session, tpp_id)
    if link is None or owner_chat_id is None:
        return None
    owner = await get_user_by_chat_id(session, owner_chat_id)
    if owner is None or link.profile_owner_id != owner.id:
        return None
    return link


async def _forget_guest(session: AsyncSession, trusted_user_id: int) -> None:
    guest = await get_user_by_id(session, trusted_user_id)
    if guest is None:
        return
    await invalidate_current_profile(guest.telegram_id)
    await invalidate_profile_lists(guest.telegram_id, "trusted")


async def delete_trusted_person(
    session: AsyncSession,
    tpp_id: int,
    *,
    owner_chat_id: int | None = None,
) -> DeleteTrustedPersonResult:
    link = await _owner_link(session, tpp_id, owner_chat_id)
    if link is None:
        return DeleteTrustedPersonResult(deleted=False)
    deleted = await delete_trusted_link(session, tpp_id)
    if deleted and owner_chat_id is not None:
        await invalidate_after_trusted_person_mutate(owner_chat_id)
        await _forget_guest(session, link.trusted_person_user_id)
    return DeleteTrustedPersonResult(deleted=deleted)


async def toggle_edit_permission(
    session: AsyncSession,
    tpp_id: int,
    *,
    owner_chat_id: int | None = None,
) -> TogglePermissionResult:
    if await _owner_link(session, tpp_id, owner_chat_id) is None:
        return TogglePermissionResult(updated=False)
    link = await toggle_trusted_edit_permission(session, tpp_id)
    if link is not None and owner_chat_id is not None:
        await invalidate_after_trusted_person_mutate(owner_chat_id)
        await _forget_guest(session, link.trusted_person_user_id)
    return TogglePermissionResult(updated=link is not None, link=link)


async def toggle_notify_permission(
    session: AsyncSession,
    tpp_id: int,
    *,
    owner_chat_id: int | None = None,
) -> TogglePermissionResult:
    if await _owner_link(session, tpp_id, owner_chat_id) is None:
        return TogglePermissionResult(updated=False)
    link = await toggle_trusted_notify_permission(session, tpp_id)
    if link is not None and owner_chat_id is not None:
        await invalidate_after_trusted_person_mutate(owner_chat_id)
        await _forget_guest(session, link.trusted_person_user_id)
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
    profile = await get_active_profile_by_id(session, profile_id)
    if profile is None or profile.user_id != sender_id:
        return CreateTrustedRequestResult(reason="not_owner")
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
    sender = await get_user_by_id(session, request.sender_id)
    if sender is not None:
        await invalidate_after_trusted_person_mutate(sender.telegram_id)
    if recipient_chat_id is not None:
        profiles = await list_trusted_profiles_for_guest(session, recipient_chat_id)
        await remember_profiles_list(recipient_chat_id, "trusted", profiles)
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
