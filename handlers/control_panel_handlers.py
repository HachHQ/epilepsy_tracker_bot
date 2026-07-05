import uuid
import os
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from aiogram.types.document import Document as AiogramDocument
from uuid import uuid4

from filters.correct_commands import UserOwnProfilesListExist
from handlers_logic.states_factories import GetExcelTableForm, TrustedPersonForm
from database.models import User, Profile, TrustedPersonProfiles, TrustedPersonRequest, RequestStatus
from database.redis_query import (
    set_redis_cached_profiles_list, set_redis_sending_timeout_ten_min, get_redis_sending_timeout_ten_min,
)
from services.cache_invalidation import invalidate_trusted_persons
from database.orm_query import (
    orm_update_list_of_trusted_profiles, orm_get_user_by_login, orm_get_trusted_users_with_full_info,
    orm_switch_trusted_profile_notify_edit_state, orm_delete_tursted_person
    )
from i18n import t
from services.redis_cache_data import get_cached_current_profile, get_cached_profiles_list, get_cached_login, get_cached_trusted_persons_agrigated_data
from services.notification_queue import NotificationQueue, TrustedContactRequest
from adapters.telegram.delivery import send_document_file
from services.to_excel import (
    build_seizures_excel,
    get_excel_template_path,
    import_seizures_from_xlsx,
)
from services.validators import validate_login_of_user_form
from services.hmac_encrypt import unpack_callback_data
from keyboards.profiles_list_kb import get_paginated_profiles_kb
from keyboards.menu_kb import get_cancel_kb
from keyboards.trusted_user_kb import (
    get_y_or_n_buttons_to_continue_process, get_y_or_n_buttons_to_finish_process, get_commiting_changing_editing_permission_kb,
    get_commiting_changing_notify_permission_kb, get_commiting_deleting_trusted_person_kb
)
from keyboards.journal_kb import get_nav_btns_for_list

control_panel_router = Router()

from config_data.pagination import TRUSTED_PERSONS_PER_PAGE as NOTES_PER_PAGE

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

@control_panel_router.callback_query(F.data == 'add_trusted')
async def process_input_trusted_person_login(callback: CallbackQuery, state: FSMContext):
    timeout_check = await get_redis_sending_timeout_ten_min(callback.message.chat.id)
    if timeout_check is not None:
        await callback.message.answer(t("trusted.rate_limit"))
        return
    await state.set_state(TrustedPersonForm.trusted_person_login)
    await callback.message.answer(t("trusted.enter_login"), reply_markup=get_cancel_kb())
    await callback.answer()

@control_panel_router.message(StateFilter(TrustedPersonForm.trusted_person_login))
async def process_search_trusted_person_by_login(message: Message, state: FSMContext, db: AsyncSession):
    if validate_login_of_user_form(message.text):
        login_redis = await get_cached_login(db, message.chat.id)
        await state.update_data(trusted_person_login=message.text)
        try:
            user = await orm_get_user_by_login(db, message.text)
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
        except Exception as e:
            print(f"Ошибка {e} при обращении к таблице users")
    else:
        await message.answer(t("user.incorrect_login"), reply_markup=get_cancel_kb())

@control_panel_router.callback_query(F.data == "trusted_person_correct", StateFilter(TrustedPersonForm.correct_trusted_person_login), UserOwnProfilesListExist())
async def process_display_profile_for_transmitting(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    profiles_redis = await get_cached_profiles_list(db, callback.message.chat.id)
    await callback.message.answer(t("trusted.select_profile"), reply_markup=get_paginated_profiles_kb(profiles_redis, to_share=True))
    await state.set_state(TrustedPersonForm.selected_profile)
    await callback.answer()

@control_panel_router.callback_query((F.data.startswith('select_profile')) & (F.data.endswith('|share')), StateFilter(TrustedPersonForm.selected_profile))
async def process_submitting_profile_to_share(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    _, profile_id, profile_name_raw = callback.data.split(':', 2)
    profile_name = profile_name_raw.split('|', 1)[0]
    await state.update_data(transmitted_profile_id=profile_id)
    await state.update_data(transmitted_profile_name=profile_name)
    await callback.message.answer(
        t("trusted.confirm_transfer", profile_name=profile_name, login=data['trusted_person_login']),
        reply_markup=get_y_or_n_buttons_to_finish_process(),
    )
    await state.set_state(TrustedPersonForm.confirm_transfer)
    await callback.answer()

@control_panel_router.callback_query(F.data == 'confirm_transfer', StateFilter(TrustedPersonForm.confirm_transfer))
async def process_confirmation(callback: CallbackQuery, state: FSMContext, db: AsyncSession, notification_queue: NotificationQueue):
    try:

        data = await state.get_data()
        recipient_login = data['trusted_person_login']
        sender_login = await get_cached_login(db, callback.message.chat.id)

        print(f"Поиск пользователя с логином: {recipient_login}")
        search_user_result = await db.execute(select(User).filter(User.telegram_id == callback.message.chat.id))
        user = search_user_result.scalars().first()
        search_recipient_result = await db.execute(select(User).filter(User.login == recipient_login))
        recipient = search_recipient_result.scalars().first()

        if not recipient:
            print("Пользователь не найден")
            await callback.message.answer(t("trusted.user_not_found_dot"))
            return
        print(f"Найден пользователь: {recipient.login} - {recipient.telegram_id}")

        search_existing_connection = await db.execute(select(TrustedPersonProfiles).filter(
            (TrustedPersonProfiles.trusted_person_user_id == user.id),
            (TrustedPersonProfiles.profile_owner_id == recipient.id),
            (TrustedPersonProfiles.profile_id == int(data['transmitted_profile_id']))
        ))
        exist_request = search_existing_connection.scalars().first()
        if exist_request:
            await callback.message.answer(t("trusted.already_trusted"))
            await callback.message.answer(t("trusted.restart_add_flow"))
            await state.clear()
            await callback.answer()
            return

        uuid_for_request = uuid.uuid4()
        short_uuid = str(uuid_for_request)[:16]

        new_request = TrustedPersonRequest(
            id = str(short_uuid),
            sender_id = user.id,
            recepient_id = recipient.id,
            transmitted_profile_id = int(data['transmitted_profile_id']),
            status = RequestStatus.PENDING
        )

        print(f"Новый запрос добавлен: {new_request}")
        await notification_queue.enqueue(TrustedContactRequest(chat_id=recipient.telegram_id,
                                              request_uuid=short_uuid,
                                              sender_login=sender_login,
                                              sender_id=user.id,
                                              transmitted_profile_id=int(data['transmitted_profile_id'])))
        db.add(new_request)
        await callback.message.answer(t("trusted.request_sent"))
        await set_redis_sending_timeout_ten_min(callback.message.chat.id, "can")
        await callback.answer()
        await state.clear()
    except Exception as e:
        await state.clear()
        print(f"Неизвестная ошибка: {e}")

@control_panel_router.callback_query(F.data == 'reject_transfer')
async def process_rejection(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(t("trusted.transfer_cancelled"))
    await callback.answer()

@control_panel_router.callback_query(F.data.startswith("p_conf") | F.data.startswith("n_conf"))
async def process_accept_trusted_person(callback: CallbackQuery, db: AsyncSession, bot: Bot):
    unpacked_callback_data = unpack_callback_data(callback.data)
    if not unpacked_callback_data:
        print("Ошибка сравнения цифровых подписей")
        return
    action, uuid_request, transmitted_profile_id, sender_id = unpacked_callback_data.split('|', 3)
    search_sender_result = await db.execute(select(User).filter(User.id == int(sender_id)))
    sender = search_sender_result.scalars().first()

    search_recepient_id_result = await db.execute(select(User).filter(User.telegram_id == callback.message.chat.id))
    recepient = search_recepient_id_result.scalars().first()

    if not recepient:
        await callback.message.answer(t("trusted.request_not_found"))
        await callback.answer()
        return

    search_request_result = await db.execute(
        select(TrustedPersonRequest).filter(
            (TrustedPersonRequest.id == uuid_request) &
            (TrustedPersonRequest.sender_id == sender.id) &
            (TrustedPersonRequest.recepient_id == recepient.id)
        )
    )
    request = search_request_result.scalars().first()

    if not request:
        await callback.message.answer(t("trusted.request_not_found_short"))
        return


    if request.status != RequestStatus.PENDING:
        await callback.message.answer(t("trusted.request_already_processed"))
        await callback.answer()
        return

    if datetime.now(timezone.utc) > request.expires_at:
            request.status = RequestStatus.EXPIRED
            await db.commit()
            await callback.message.answer(t("trusted.request_expired"))
            await bot.send_message(chat_id=sender.telegram_id, text=t("trusted.recipient_timeout", login=recepient.login))
            await callback.answer()
            return

    if action == "p_conf":
        request.status = RequestStatus.ACCEPTED

        new_trusted_person_profile = TrustedPersonProfiles(
            trusted_person_user_id = recepient.id,
            profile_owner_id = sender.id,
            profile_id = int(transmitted_profile_id),
        )
        db.add(new_trusted_person_profile)

        await bot.send_message(chat_id=sender.telegram_id, text=t("trusted.recipient_confirmed", login=recepient.login))

        profiles = await orm_update_list_of_trusted_profiles(db, callback.message.chat.id)

        await set_redis_cached_profiles_list(callback.message.chat.id, "trusted", profiles)
        await invalidate_trusted_persons(callback.message.chat.id)

        await callback.message.answer(t("trusted.request_confirmed"))

        await callback.answer()

        await db.commit()


    if action == "n_conf":
        request.status = RequestStatus.REJECTED

        await bot.send_message(chat_id=sender.telegram_id, text=t("trusted.recipient_rejected", login=recepient.login))

        await callback.message.answer(t("trusted.request_rejected"))
        await callback.answer()

        await db.commit()

    await callback.answer()

@control_panel_router.callback_query(F.data == "trusted_person_control_panel")
async def process_trusted_person_control_panel(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    trusted_persons = await orm_get_trusted_users_with_full_info(db, callback.message.chat.id)
    if len(trusted_persons) == 0:
        await callback.message.answer(t("trusted.no_trusted_persons"))
    text = t("trusted.list_header")
    text += display_trusted_profiles(trusted_persons, 0)
    await callback.message.answer(text, parse_mode='HTML', reply_markup=get_nav_btns_for_list(len(trusted_persons), NOTES_PER_PAGE, 0, 'trusted_person_control_panel'))
    await callback.answer()

@control_panel_router.callback_query(F.data.startswith('trusted_person_control_panel'))
async def process_pagination_of_trusted_persons_control_panel(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, page = callback.data.split(':', 1)
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, callback.message.chat.id)
    if len(trusted_persons) == 0:
        await callback.message.answer(t("trusted.no_trusted_persons"))
    text = t("trusted.list_header")
    text += display_trusted_profiles(trusted_persons, page)
    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_nav_btns_for_list(len(trusted_persons), NOTES_PER_PAGE, page, 'trusted_person_control_panel'))
    await callback.answer()

def find_trusted_record_by_id(trusted_persons, trusted_profile_id: int):
        for item in trusted_persons:
            if item['permissions']['id'] == trusted_profile_id:
                return item
        return None

@control_panel_router.message(F.text.startswith("/tpshow"))
async def process_showing_tp_detailed_info(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    tpp_id = message.text.split('_', 1)[1]
    if not tpp_id.isnumeric():
        await message.answer(t("trusted.invalid_index"))
        return
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, message.chat.id)
    if int(tpp_id) not in [int(tp['permissions']['id']) for tp in trusted_persons]:
        await message.answer(t("trusted.record_not_found"))
        return
    trusted_person_info = find_trusted_record_by_id(trusted_persons, int(tpp_id))
    username = (
        '@' + trusted_person_info['trusted_user']['telegram_username']
        if trusted_person_info['trusted_user']['telegram_username'] is not None
        else t("trusted.unknown")
    )
    text = t(
        "trusted.detail_view",
        login=trusted_person_info['trusted_user']['login'],
        name=trusted_person_info['trusted_user']['name'],
        fullname=_trusted_unknown(trusted_person_info['trusted_user']['telegram_fullname']),
        username=username,
        profile_name=trusted_person_info['profile']['profile_name'],
        since=str(trusted_person_info['permissions']['created_at'])[:10],
        can_edit=_trusted_permission_label(trusted_person_info['permissions']['can_edit']),
        get_notification=_trusted_permission_label(trusted_person_info['permissions']['get_notification']),
        id=tpp_id,
    )
    await message.answer(text, parse_mode='HTML')

@control_panel_router.message(F.text.startswith("/tpeditcned_"))
async def process_change_editing_permission(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    tpp_id = message.text.split('_', 1)[1]
    if not tpp_id.isnumeric():
        await message.answer(t("trusted.invalid_index"))
        return
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, message.chat.id)
    if int(tpp_id) not in [int(tp['permissions']['id']) for tp in trusted_persons]:
        await message.answer(t("trusted.record_not_found"))
        return
    trusted_person_info = find_trusted_record_by_id(trusted_persons, int(tpp_id))
    if trusted_person_info['permissions']['can_edit']:
        await message.answer(
            t("trusted.deny_edit", login=trusted_person_info['trusted_user']['login']),
            parse_mode='HTML',
            reply_markup=get_commiting_changing_editing_permission_kb(tpp_id),
        )
    elif not trusted_person_info['permissions']['can_edit']:
        await message.answer(
            t("trusted.allow_edit", login=trusted_person_info['trusted_user']['login']),
            parse_mode='HTML',
            reply_markup=get_commiting_changing_editing_permission_kb(tpp_id),
        )


@control_panel_router.callback_query(F.data.startswith("tpchangeediting"))
async def process_commit_changing_editing_permission(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, answer, tpp_id = callback.data.split(':', 2)
    if answer == "yes":
        await orm_switch_trusted_profile_notify_edit_state(db, int(tpp_id), switch_edit=True)
        await callback.message.edit_text(t("trusted.permissions_saved"))
        await invalidate_trusted_persons(callback.message.chat.id)
    else:
        await callback.message.edit_text(t("trusted.permissions_cancelled"))
    await callback.answer()

@control_panel_router.message(F.text.startswith("/tpeditntfyprm"))
async def process_change_getting_notification_permission(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    tpp_id = message.text.split('_', 1)[1]
    if not tpp_id.isnumeric():
        await message.answer(t("trusted.invalid_index"))
        return
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, message.chat.id)
    if int(tpp_id) not in [int(tp['permissions']['id']) for tp in trusted_persons]:
        await message.answer(t("trusted.record_not_found"))
        return
    trusted_person_info = find_trusted_record_by_id(trusted_persons, int(tpp_id))
    if trusted_person_info['permissions']['get_notification']:
        await message.answer(
            t("trusted.deny_notify", login=trusted_person_info['trusted_user']['login']),
            parse_mode='HTML',
            reply_markup=get_commiting_changing_notify_permission_kb(tpp_id),
        )
    else:
        await message.answer(
            t("trusted.allow_notify", login=trusted_person_info['trusted_user']['login']),
            parse_mode='HTML',
            reply_markup=get_commiting_changing_notify_permission_kb(tpp_id),
        )

@control_panel_router.callback_query(F.data.startswith("tpchangegettingnotify"))
async def process_delete_trusted_person(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, answer, tpp_id = callback.data.split(':', 2)
    if answer == "yes":
        await orm_switch_trusted_profile_notify_edit_state(db, int(tpp_id), getting_notify=True)
        await callback.message.edit_text(t("trusted.permissions_saved"))
        await invalidate_trusted_persons(callback.message.chat.id)
    else:
        await callback.message.edit_text(t("trusted.permissions_cancelled"))
    await callback.answer()

@control_panel_router.message(F.text.startswith("/tpdelete"))
async def process_deleting_trusted_person(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    tpp_id = message.text.split('_', 1)[1]
    if not tpp_id.isnumeric():
        await message.answer(t("trusted.invalid_index"))
        return
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, message.chat.id)
    if int(tpp_id) not in [int(tp['permissions']['id']) for tp in trusted_persons]:
        await message.answer(t("trusted.record_not_found"))
        return
    await message.answer(t("trusted.delete_confirm"), reply_markup=get_commiting_deleting_trusted_person_kb(tpp_id))

@control_panel_router.callback_query(F.data.startswith("tpdeleting"))
async def process_delete_trusted_person(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, answer, tpp_id = callback.data.split(':', 2)
    if answer == "yes":
        if answer == 'yes':
            res = await orm_delete_tursted_person(db, int(tpp_id))
            if res:
                await callback.message.edit_text(t("trusted.delete_success"))
                await invalidate_trusted_persons(callback.message.chat.id)
            else:
                await callback.message.edit_text(t("trusted.record_not_found"))
    else:
        await callback.message.edit_text(t("trusted.delete_cancelled"))
    await callback.answer()

@control_panel_router.callback_query(F.data == 'export_data')
async def process_export_excel_data_by_profile(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    prof = await get_cached_current_profile(db, callback.message.chat.id)
    file_path = await build_seizures_excel(int(prof.split('|')[0]), db)
    await send_document_file(bot, callback.message.chat.id, file_path)
    await callback.answer()

@control_panel_router.callback_query(F.data == 'import_data')
async def process_import_excel_data_by_profile(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    await send_document_file(
        bot,
        callback.message.chat.id,
        get_excel_template_path(),
        caption=t("import.template_caption"),
        remove_after=False,
    )
    await callback.message.answer(t("import.download_template"))
    await state.set_state(GetExcelTableForm.get_xlsx_file)
    await callback.answer()

@control_panel_router.message(F.document, StateFilter(GetExcelTableForm))
async def handle_excel_upload(message: Message, db: AsyncSession, state: FSMContext, bot: Bot):
    if message.document.file_name.endswith('.xlsx'):
        try:
            prof = await get_cached_current_profile(db, message.chat.id)
            login = await get_cached_login(db, message.chat.id)
            file_id = str(uuid4())
            file_path = f"import_temp/{file_id}.xlsx"
            os.makedirs("import_temp", exist_ok=True)
            document = message.document
            file = await bot.get_file(document.file_id)
            await bot.download_file(file.file_path, destination=file_path)
            valid_count, failed_rows = await import_seizures_from_xlsx(
                file_path, db=db, profile_id=int(prof.split('|')[0]), login=login,
            )
            text = t("import.import_complete", valid_count=valid_count, failed_count=len(failed_rows))
            await message.answer(text)
            if failed_rows:
                import pandas as pd
                df_failed = pd.DataFrame(failed_rows)
                failed_file_path = f"import_temp/{file_id}_errors.xlsx"
                df_failed.to_excel(failed_file_path, index=False)

                await message.answer_document(
                    document=FSInputFile(failed_file_path),
                    caption=t("import.failed_rows_caption"),
                )
                os.remove(failed_file_path)

        except Exception as e:
            await message.answer(t("import.file_processing_error", error=str(e)))
        finally:
            await state.clear()
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        await message.answer(t("import.xlsx_required"))
