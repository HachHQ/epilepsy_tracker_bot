import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.anchor import live_message
from adapters.telegram.notification_queue import NotificationQueue, TrustedContactRequest
from config_data.pagination import TRUSTED_PERSONS_PER_PAGE as NOTES_PER_PAGE
from database.repositories.profiles import get_active_profile_by_id
from database.repositories.users import get_user_by_chat_id, get_user_by_id
from filters.correct_commands import UserOwnProfilesListExist
from handlers_logic.states_factories import TrustedPersonForm
from i18n import t
from keyboards.menu_kb import get_cancel_kb
from keyboards.profiles_list_kb import get_paginated_profiles_kb
from keyboards.trusted_user_kb import (
    get_commiting_changing_editing_permission_kb,
    get_commiting_changing_notify_permission_kb,
    get_commiting_deleting_trusted_person_kb,
    get_trusted_card_kb,
    get_trusted_persons_kb,
    get_y_or_n_buttons_to_continue_process,
    get_y_or_n_buttons_to_finish_process,
)
from services.cache_keys import TRUSTED_LOOKUP_LIMIT
from services.hmac_encrypt import unpack_callback_data
from services.redis_cache_data import (
    count_trusted_lookup,
    get_cached_login,
    get_cached_profiles_list,
    get_trusted_request_cooldown,
    remember_trusted_request_cooldown,
)
from services.validators import validate_login_of_user_form
from use_cases import trusted_persons as trusted_use_cases

trusted_person_router = Router()
logger = logging.getLogger(__name__)

def _trusted_unknown(value):
    return value if value is not None else t("trusted.unknown")

def _trusted_permission_label(enabled: bool) -> str:
    return t("trusted.permission_yes") if enabled else t("trusted.permission_no")

def display_trusted_profiles(trusted_profiles, current_page):
    current_page = int(current_page)
    start_index = current_page * NOTES_PER_PAGE
    end_index = int(start_index) + NOTES_PER_PAGE
    trusted_persons_on_page = trusted_profiles[start_index:end_index]
    text = ""
    for tp in trusted_persons_on_page:
        username = (
            '@' + tp['trusted_user']['telegram_username']
            if tp['trusted_user']['telegram_username'] is not None
            else t("trusted.unknown")
        )
        text += t(
            "trusted.list_item",
            login=tp['trusted_user']['login'],
            name=tp['trusted_user']['name'],
            username=username,
            fullname=_trusted_unknown(tp['trusted_user']['telegram_fullname']),
            profile_name=tp['profile']['profile_name'],
            id=tp['permissions']['id'],
        )
    return text

@trusted_person_router.callback_query(F.data == 'add_trusted')
async def process_input_trusted_person_login(callback: CallbackQuery, state: FSMContext):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    timeout_check = await get_trusted_request_cooldown(message.chat.id)
    if timeout_check is not None:
        await message.answer(t("trusted.rate_limit"))
        return
    await state.set_state(TrustedPersonForm.trusted_person_login)
    await message.answer(t("trusted.enter_login"), reply_markup=get_cancel_kb())
    await callback.answer()

@trusted_person_router.message(StateFilter(TrustedPersonForm.trusted_person_login))
async def process_search_trusted_person_by_login(message: Message, state: FSMContext, db: AsyncSession):
    if await count_trusted_lookup(message.chat.id) > TRUSTED_LOOKUP_LIMIT:
        await message.answer(t("trusted.lookup_rate_limit"))
        return
    if message.text and validate_login_of_user_form(message.text):
        login_redis = await get_cached_login(db, message.chat.id)
        await state.update_data(trusted_person_login=message.text)
        try:
            user = await trusted_use_cases.find_user_by_login(db, message.text)
            if not user:
                await message.answer(t("trusted.user_not_found"))
                return

            if user.login == login_redis:
                await message.answer(t("trusted.self_trust_forbidden"))
                return

            await message.answer(
                t(
                    "trusted.user_found",
                    login=user.login,
                    fullname=user.telegram_fullname,
                    username=user.telegram_username,
                ),
                reply_markup=get_y_or_n_buttons_to_continue_process(),
            )
            await state.set_state(TrustedPersonForm.correct_trusted_person_login)
        except Exception:
            logger.exception("Failed to look up trusted person by login")
    else:
        await message.answer(t("user.incorrect_login"), reply_markup=get_cancel_kb())

@trusted_person_router.callback_query(F.data == "trusted_person_correct", StateFilter(TrustedPersonForm.correct_trusted_person_login), UserOwnProfilesListExist())
async def process_display_profile_for_transmitting(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    profiles_redis = await get_cached_profiles_list(db, message.chat.id)
    await message.answer(
        t("trusted.select_profile"),
        reply_markup=get_paginated_profiles_kb(profiles_redis or [], to_share=True),
    )
    await state.set_state(TrustedPersonForm.selected_profile)
    await callback.answer()

@trusted_person_router.callback_query((F.data.startswith('select_profile')) & (F.data.endswith('|share')), StateFilter(TrustedPersonForm.selected_profile))
async def process_submitting_profile_to_share(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    data = await state.get_data()
    _, profile_id, profile_name_raw = payload.split(':', 2)
    profile_name = profile_name_raw.split('|', 1)[0]
    owner = await get_user_by_chat_id(db, message.chat.id)
    profile = await get_active_profile_by_id(db, int(profile_id))
    if owner is None or profile is None or profile.user_id != owner.id:
        await message.answer(t("trusted.profile_not_owned"))
        await callback.answer()
        return
    await state.update_data(transmitted_profile_id=profile_id)
    await state.update_data(transmitted_profile_name=profile_name)
    await message.answer(
        t("trusted.confirm_transfer", profile_name=profile_name, login=data['trusted_person_login']),
        reply_markup=get_y_or_n_buttons_to_finish_process(),
    )
    await state.set_state(TrustedPersonForm.confirm_transfer)
    await callback.answer()

@trusted_person_router.callback_query(F.data == 'confirm_transfer', StateFilter(TrustedPersonForm.confirm_transfer))
async def process_confirmation(callback: CallbackQuery, state: FSMContext, db: AsyncSession, notification_queue: NotificationQueue):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    try:

        data = await state.get_data()
        recipient_login = data['trusted_person_login']
        sender_login = await get_cached_login(db, message.chat.id)

        logger.info("Searching trusted person recipient: %s", recipient_login)
        user = await get_user_by_chat_id(db, message.chat.id)
        recipient = await trusted_use_cases.find_user_by_login(db, recipient_login)

        if not user or not recipient or not sender_login:
            logger.warning("Trusted person recipient not found: %s", recipient_login)
            await message.answer(t("trusted.user_not_found_dot"))
            return
        logger.info("Found recipient %s (telegram_id=%s)", recipient.login, recipient.telegram_id)

        if await trusted_use_cases.trusted_link_exists(
            db,
            trusted_person_user_id=recipient.id,
            profile_owner_id=user.id,
            profile_id=int(data["transmitted_profile_id"]),
        ):
            await message.answer(t("trusted.already_trusted"))
            await message.answer(t("trusted.restart_add_flow"))
            await state.clear()
            await callback.answer()
            return

        create_result = await trusted_use_cases.create_trusted_request(
            db,
            sender_id=user.id,
            recipient_id=recipient.id,
            profile_id=int(data["transmitted_profile_id"]),
        )
        if create_result.reason == "not_owner" or create_result.request_uuid is None:
            await message.answer(t("trusted.profile_not_owned"))
            await state.clear()
            await callback.answer()
            return

        logger.info("Created trusted person request %s", create_result.request_uuid)
        await notification_queue.enqueue(
            TrustedContactRequest(
                chat_id=recipient.telegram_id,
                request_uuid=create_result.request_uuid,
                sender_login=sender_login,
                sender_id=user.id,
                transmitted_profile_id=int(data["transmitted_profile_id"]),
            )
        )
        await message.answer(t("trusted.request_sent"))
        await remember_trusted_request_cooldown(message.chat.id, "can")
        await callback.answer()
        await state.clear()
    except Exception:
        await state.clear()
        logger.exception("Failed to confirm trusted person transfer")
        await message.answer(t("trusted.request_failed"))
        await callback.answer()

@trusted_person_router.callback_query(F.data == 'reject_transfer')
async def process_rejection(callback: CallbackQuery, state: FSMContext):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    await state.clear()
    await message.answer(t("trusted.transfer_cancelled"))
    await callback.answer()

@trusted_person_router.callback_query(F.data.startswith("p_conf") | F.data.startswith("n_conf"))
async def process_accept_trusted_person(callback: CallbackQuery, db: AsyncSession, bot: Bot):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    unpacked_callback_data = unpack_callback_data(payload)
    if not unpacked_callback_data:
        logger.warning("Trusted person callback signature mismatch")
        return
    action, uuid_request, transmitted_profile_id, sender_id = unpacked_callback_data.split("|", 3)
    sender = await get_user_by_id(db, int(sender_id))
    recepient = await get_user_by_chat_id(db, message.chat.id)

    if not recepient or not sender:
        await message.answer(t("trusted.request_not_found"))
        await callback.answer()
        return

    if action == "p_conf":
        result = await trusted_use_cases.accept_trusted_request(
            db,
            request_id=uuid_request,
            sender_id=int(sender_id),
            recipient_id=recepient.id,
            recipient_chat_id=message.chat.id,
        )
        if result.reason == "not_found":
            await message.answer(t("trusted.request_not_found_short"))
            await callback.answer()
            return
        if result.reason == "already_processed":
            await message.answer(t("trusted.request_already_processed"))
            await callback.answer()
            return
        if result.reason == "expired":
            await db.commit()
            await message.answer(t("trusted.request_expired"))
            await bot.send_message(
                chat_id=sender.telegram_id,
                text=t("trusted.recipient_timeout", login=recepient.login),
            )
            await callback.answer()
            return

        await bot.send_message(
            chat_id=sender.telegram_id,
            text=t("trusted.recipient_confirmed", login=recepient.login),
        )
        await message.answer(t("trusted.request_confirmed"))
        await callback.answer()
        await db.commit()
        return

    if action == "n_conf":
        reject_result = await trusted_use_cases.reject_trusted_request(
            db,
            request_id=uuid_request,
            sender_id=int(sender_id),
            recipient_id=recepient.id,
        )
        if reject_result.reason == "not_found":
            await message.answer(t("trusted.request_not_found_short"))
            await callback.answer()
            return
        if reject_result.reason == "already_processed":
            await message.answer(t("trusted.request_already_processed"))
            await callback.answer()
            return

        await bot.send_message(
            chat_id=sender.telegram_id,
            text=t("trusted.recipient_rejected", login=recepient.login),
        )
        await message.answer(t("trusted.request_rejected"))
        await callback.answer()
        await db.commit()

def _trusted_page_markup(records: list[dict], page: int):
    return get_trusted_persons_kb(records, page=page, page_size=NOTES_PER_PAGE)


def _card_text(record: dict) -> str:
    username = (
        "@" + record["trusted_user"]["telegram_username"]
        if record["trusted_user"]["telegram_username"] is not None
        else t("trusted.unknown")
    )
    return t(
        "trusted.detail_view",
        login=record["trusted_user"]["login"],
        name=record["trusted_user"]["name"],
        fullname=_trusted_unknown(record["trusted_user"]["telegram_fullname"]),
        username=username,
        profile_name=record["profile"]["profile_name"],
        since=str(record["permissions"]["created_at"])[:10],
        can_edit=_trusted_permission_label(record["permissions"]["can_edit"]),
        get_notification=_trusted_permission_label(record["permissions"]["get_notification"]),
    )


async def _owner_record(db: AsyncSession, chat_id: int, link_id: int):
    records = await trusted_use_cases.list_owner_trusted_persons(db, chat_id)
    for item in records:
        if int(item["permissions"]["id"]) == link_id:
            return item
    return None


@trusted_person_router.callback_query(F.data == "trusted_person_control_panel")
async def process_trusted_person_control_panel(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    await state.clear()
    trusted_persons = await trusted_use_cases.list_owner_trusted_persons(db, message.chat.id)
    if not trusted_persons:
        await message.answer(t("trusted.no_trusted_persons"))
        await callback.answer()
        return
    text = t("trusted.list_header") + display_trusted_profiles(trusted_persons, 0)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=_trusted_page_markup(trusted_persons, 0),
    )
    await callback.answer()


@trusted_person_router.callback_query(F.data.startswith("trusted_person_control_panel:"))
async def process_pagination_of_trusted_persons_control_panel(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    await state.clear()
    _, page = payload.split(":", 1)
    if not page.isdigit():
        await callback.answer()
        return
    trusted_persons = await trusted_use_cases.list_owner_trusted_persons(db, message.chat.id)
    if not trusted_persons:
        await message.answer(t("trusted.no_trusted_persons"))
        await callback.answer()
        return
    text = t("trusted.list_header") + display_trusted_profiles(trusted_persons, int(page))
    await message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=_trusted_page_markup(trusted_persons, int(page)),
    )
    await callback.answer()


@trusted_person_router.callback_query(F.data.startswith("tp_card:"))
async def process_trusted_card(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    link_id = payload.split(":", 1)[1]
    if not link_id.isdigit():
        await callback.answer()
        return
    record = await _owner_record(db, message.chat.id, int(link_id))
    if record is None:
        await message.answer(t("trusted.record_not_found"))
        await callback.answer()
        return
    await message.answer(
        _card_text(record),
        parse_mode="HTML",
        reply_markup=get_trusted_card_kb(
            int(link_id),
            can_edit=bool(record["permissions"]["can_edit"]),
            get_notification=bool(record["permissions"]["get_notification"]),
        ),
    )
    await callback.answer()


@trusted_person_router.callback_query(F.data.startswith("tp_ask_edit:"))
async def process_ask_edit_permission(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    link_id = payload.split(":", 1)[1]
    record = await _owner_record(db, message.chat.id, int(link_id))
    if record is None:
        await message.answer(t("trusted.record_not_found"))
        await callback.answer()
        return
    prompt = "trusted.deny_edit" if record["permissions"]["can_edit"] else "trusted.allow_edit"
    await message.answer(
        t(prompt, login=record["trusted_user"]["login"]),
        parse_mode="HTML",
        reply_markup=get_commiting_changing_editing_permission_kb(int(link_id)),
    )
    await callback.answer()


@trusted_person_router.callback_query(F.data.startswith("tpchangeediting"))
async def process_commit_changing_editing_permission(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    _, answer, tpp_id = payload.split(":", 2)
    if answer == "yes":
        result = await trusted_use_cases.toggle_edit_permission(
            db, int(tpp_id), owner_chat_id=message.chat.id
        )
        await message.edit_text(
            t("trusted.permissions_saved") if result.updated else t("trusted.record_not_found")
        )
    else:
        await message.edit_text(t("trusted.permissions_cancelled"))
    await callback.answer()


@trusted_person_router.callback_query(F.data.startswith("tp_ask_notify:"))
async def process_ask_notify_permission(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    link_id = payload.split(":", 1)[1]
    record = await _owner_record(db, message.chat.id, int(link_id))
    if record is None:
        await message.answer(t("trusted.record_not_found"))
        await callback.answer()
        return
    prompt = "trusted.deny_notify" if record["permissions"]["get_notification"] else "trusted.allow_notify"
    await message.answer(
        t(prompt, login=record["trusted_user"]["login"]),
        parse_mode="HTML",
        reply_markup=get_commiting_changing_notify_permission_kb(int(link_id)),
    )
    await callback.answer()


@trusted_person_router.callback_query(F.data.startswith("tpchangegettingnotify"))
async def process_commit_changing_notify_permission(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    _, answer, tpp_id = payload.split(":", 2)
    if answer == "yes":
        result = await trusted_use_cases.toggle_notify_permission(
            db, int(tpp_id), owner_chat_id=message.chat.id
        )
        await message.edit_text(
            t("trusted.permissions_saved") if result.updated else t("trusted.record_not_found")
        )
    else:
        await message.edit_text(t("trusted.permissions_cancelled"))
    await callback.answer()


@trusted_person_router.callback_query(F.data.startswith("tp_ask_delete:"))
async def process_ask_delete_trusted_person(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    link_id = payload.split(":", 1)[1]
    record = await _owner_record(db, message.chat.id, int(link_id))
    if record is None:
        await message.answer(t("trusted.record_not_found"))
        await callback.answer()
        return
    await message.answer(
        t("trusted.delete_confirm"),
        reply_markup=get_commiting_deleting_trusted_person_kb(int(link_id)),
    )
    await callback.answer()


@trusted_person_router.callback_query(F.data.startswith("tpdeleting"))
async def process_commit_deleting_trusted_person(callback: CallbackQuery, db: AsyncSession):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    payload = callback.data
    if payload is None:
        await callback.answer()
        return
    _, answer, tpp_id = payload.split(":", 2)
    if answer == "yes":
        result = await trusted_use_cases.delete_trusted_person(
            db, int(tpp_id), owner_chat_id=message.chat.id
        )
        await message.edit_text(
            t("trusted.delete_success") if result.deleted else t("trusted.record_not_found")
        )
    else:
        await message.edit_text(t("trusted.delete_cancelled"))
    await callback.answer()
