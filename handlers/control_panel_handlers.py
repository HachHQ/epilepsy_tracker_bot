import uuid
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone

from filters.correct_commands import UserOwnProfilesListExist
from handlers_logic.states_factories import TrustedPersonForm
from database.models import User, Profile, TrustedPersonProfiles, TrustedPersonRequest, RequestStatus
from database.redis_query import (
    set_redis_cached_profiles_list, set_redis_sending_timeout_ten_min, get_redis_sending_timeout_ten_min,
    delete_redis_trusted_persons
)
from database.orm_query import (
    orm_update_list_of_trusted_profiles, orm_get_user_by_login, orm_get_trusted_users_with_full_info,
    orm_switch_trusted_profile_notify_edit_state, orm_delete_tursted_person
    )
from lexicon.lexicon import LEXICON_RU
from services.redis_cache_data import get_cached_profiles_list, get_cached_login, get_cached_trusted_persons_agrigated_data
from services.notification_queue import NotificationQueue
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

NOTES_PER_PAGE = 3

def display_trusted_profiles(trusted_profiles, current_page):
    current_page = int(current_page)
    start_index = current_page * NOTES_PER_PAGE
    end_index = int(start_index) + NOTES_PER_PAGE
    trusted_persons_on_page = trusted_profiles[start_index:end_index]
    text = ""
    for tp in trusted_persons_on_page:
        line = (
            f"Логин и имя в системе - {tp['trusted_user']['login']} | {tp['trusted_user']['name']}\n"
            f"Юзернейм в телеграме - {'@' + tp['trusted_user']['telegram_username'] if tp['trusted_user']['telegram_username'] is not None else "Неизвестно"}\n"
            f"Полное имя в телеграме - {tp['trusted_user']['telegram_fullname'] if tp['trusted_user']['telegram_fullname'] is not None else "Неизвестно"}\n"
            f"Владеет профилем - <b>{tp['profile']['profile_name']}</b> /tpshow_{tp['permissions']['id']}\n\n"
        )
        text += line
    return text

@control_panel_router.callback_query(F.data == 'add_trusted')
async def process_input_trusted_person_login(callback: CallbackQuery, state: FSMContext):
    timeout_check = await get_redis_sending_timeout_ten_min(callback.message.chat.id)
    if timeout_check is not None:
        await callback.message.answer("Запрос на добавление доверенного лица можно отправлять раз в 10 минут")
        return
    await state.set_state(TrustedPersonForm.trusted_person_login)
    await callback.message.answer("Введите логин профиля пользователя, которому хотите доверить свой профиль: ", reply_markup=get_cancel_kb())
    await callback.answer()

@control_panel_router.message(StateFilter(TrustedPersonForm.trusted_person_login))
async def process_search_trusted_person_by_login(message: Message, state: FSMContext, db: AsyncSession):
    if validate_login_of_user_form(message.text):
        login_redis = await get_cached_login(db, message.chat.id)
        await state.update_data(trusted_person_login=message.text)
        try:
            user = await orm_get_user_by_login(db, message.text)
            if not user:
                await message.answer("Пользователь не найден")
                return

            if user.login == login_redis:
                await message.answer("Нельзя стать доверенным лицом самого себя)")
                return

            await message.answer(f"Пользователь с логином {user.login} найден.\nЕго полное имя в телеграме - {user.telegram_fullname}\nЕго юзернейм в телеграме - {user.telegram_username}\n\nЕсли данные верны - нажмите 'Да', если нет - нажмите 'Нет'", reply_markup=get_y_or_n_buttons_to_continue_process())
            await state.set_state(TrustedPersonForm.correct_trusted_person_login)
        except Exception as e:
            print(f"Ошибка {e} при обращении к таблице users")
    else:
        await message.answer(LEXICON_RU['incorrect_login'], reply_markup=get_cancel_kb())

@control_panel_router.callback_query(F.data == "trusted_person_correct", StateFilter(TrustedPersonForm.correct_trusted_person_login), UserOwnProfilesListExist())
async def process_display_profile_for_transmitting(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    profiles_redis = await get_cached_profiles_list(db, callback.message.chat.id)
    await callback.message.answer("Выберите профиль, которым хотите поделиться: ", reply_markup=get_paginated_profiles_kb(profiles_redis, to_share=True))
    await state.set_state(TrustedPersonForm.selected_profile)
    await callback.answer()

@control_panel_router.callback_query((F.data.startswith('select_profile')) & (F.data.endswith('|share')), StateFilter(TrustedPersonForm.selected_profile))
async def process_submitting_profile_to_share(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    _, profile_id, profile_name_raw = callback.data.split(':', 2)
    profile_name = profile_name_raw.split('|', 1)[0]
    await state.update_data(transmitted_profile_id=profile_id)
    await state.update_data(transmitted_profile_name=profile_name)
    await callback.message.answer(f"Доверить данные вашего профиля {profile_name} пользователю {data['trusted_person_login']}?", reply_markup=get_y_or_n_buttons_to_finish_process())
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
            await callback.message.answer("Пользователь не найден.")
            return
        print(f"Найден пользователь: {recipient.login} - {recipient.telegram_id}")

        search_existing_connection = await db.execute(select(TrustedPersonProfiles).filter(
            (TrustedPersonProfiles.trusted_person_user_id == user.id),
            (TrustedPersonProfiles.profile_owner_id == recipient.id),
            (TrustedPersonProfiles.profile_id == int(data['transmitted_profile_id']))
        ))
        exist_request = search_existing_connection.scalars().first()
        if exist_request:
            await callback.message.answer("Этот пользователь уже является вашим доверенным лицом и имеет доступ к этому профилю.")
            await callback.message.answer("Начните заполнение сценария добавления доверенного лица заново.")
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
        await notification_queue.send_trusted_contact_request(chat_id=recipient.telegram_id,
                                              request_uuid=short_uuid,
                                              sender_login=sender_login,
                                              sender_id=user.id,
                                              transmitted_profile_id=int(data['transmitted_profile_id']),)
        db.add(new_request)
        await callback.message.answer("Запрос отправлен и будет активен в течение десяти минут.")
        await set_redis_sending_timeout_ten_min(callback.message.chat.id, "can")
        await callback.answer()
        await state.clear()
    except Exception as e:
        await state.clear()
        print(f"Неизвестная ошибка: {e}")

@control_panel_router.callback_query(F.data == 'reject_transfer')
async def process_rejection(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Заполнение сценария заполнения передачи профиля доверенному лицу отменено.")
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
        await callback.message.answer("Запрос не найден. Попросите пользователя отправить новый.")
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
        await callback.message.answer("Запрос не найден.")
        return


    if request.status != RequestStatus.PENDING:
        await callback.message.answer("Запрос уже был обработан ранее.")
        await callback.answer()
        return

    if datetime.now(timezone.utc) > request.expires_at:
            request.status = RequestStatus.EXPIRED
            await db.commit()
            await callback.message.answer("Время запроса истекло")
            await bot.send_message(chat_id=sender.telegram_id, text=f"Пользователь {recepient.login} не успел принять запрос.")
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

        await bot.send_message(chat_id=sender.telegram_id, text=f"Пользователь {recepient.login} подтвердил запрос.")

        profiles = await orm_update_list_of_trusted_profiles(db, callback.message.chat.id)

        await set_redis_cached_profiles_list(callback.message.chat.id, "trusted", profiles)
        await delete_redis_trusted_persons(callback.message.chat.id)

        await callback.message.answer("Запрос подтвержден")

        await callback.answer()

        await db.commit()


    if action == "n_conf":
        request.status = RequestStatus.REJECTED

        await bot.send_message(chat_id=sender.telegram_id, text=f"Пользователь {recepient.login} отклонил запрос.")

        await callback.message.answer("Запрос отклонен")
        await callback.answer()

        await db.commit()

    await callback.answer()

@control_panel_router.callback_query(F.data == "trusted_person_control_panel")
async def process_trusted_person_control_panel(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    trusted_persons = await orm_get_trusted_users_with_full_info(db, callback.message.chat.id)
    if len(trusted_persons) == 0:
        await callback.message.answer("У вас нет доверенных лиц")
    text = "Ваши доверенные лица\n\n"
    text += display_trusted_profiles(trusted_persons, 0)
    await callback.message.answer(text, parse_mode='HTML', reply_markup=get_nav_btns_for_list(len(trusted_persons), NOTES_PER_PAGE, 0, 'trusted_person_control_panel'))
    await callback.answer()

@control_panel_router.callback_query(F.data.startswith('trusted_person_control_panel'))
async def process_pagination_of__seizures_list(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, page = callback.data.split(':', 1)
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, callback.message.chat.id)
    if len(trusted_persons) == 0:
        await callback.message.answer("У вас нет доверенных лиц")
    text = "Ваши доверенные лица\n\n"
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
        await message.answer("Неверный индекс записи.")
        return
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, message.chat.id)
    if int(tpp_id) not in [int(tp['permissions']['id']) for tp in trusted_persons]:
        await message.answer("Для вашего пользователя нет такой записи.")
        return
    trusted_person_info = find_trusted_record_by_id(trusted_persons, int(tpp_id))
    text = (
        f"Данные доверенного лица <b>{trusted_person_info['trusted_user']['login']}</b>\n\n"
        f"Имя в системе - {trusted_person_info['trusted_user']['name']}\n"
        f"Полное имя в телеграме - {trusted_person_info['trusted_user']['telegram_fullname'] if trusted_person_info['trusted_user']['telegram_fullname'] is not None else "Неизвестно"}\n"
        f"Юзернейм в телеграме - {'@' + trusted_person_info['trusted_user']['telegram_username'] if trusted_person_info['trusted_user']['telegram_username'] is not None else "Неизвестно"}\n"
        f"Владеет профилем <b>{trusted_person_info['profile']['profile_name']}</b> с {str(trusted_person_info['permissions']['created_at'])[:10]}\n\n"

        f"Редактирование/внесение данных о приступах: <b>{"✅ Да" if trusted_person_info['permissions']['can_edit'] else "❌ Нет"}</b> - "
        f"/tpchangecanedit_{tpp_id}\n"
        f"Получает экстренные уведомления: <b>{"✅ Да" if trusted_person_info['permissions']['get_notification'] else "❌ Нет"}</b> - "
        f"/tpchangecanrecievenotify_{tpp_id}\n\n"
        f"Удалить доверенное лицо - /tpdelete_{tpp_id}"
    )
    await message.answer(text, parse_mode='HTML')

@control_panel_router.message(F.text.startswith("/tpchangecanedit"))
async def process_change_editing_permission(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    tpp_id = message.text.split('_', 1)[1]
    if not tpp_id.isnumeric():
        await message.answer("Неверный индекс записи.")
        return
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, message.chat.id)
    if int(tpp_id) not in [int(tp['permissions']['id']) for tp in trusted_persons]:
        await message.answer("Для вашего пользователя нет такой записи.")
        return
    trusted_person_info = find_trusted_record_by_id(trusted_persons, int(tpp_id))
    if trusted_person_info['permissions']['can_edit']:
        await message.answer(f"Вы хотите <b>запретить</b> пользователю {trusted_person_info['trusted_user']['login']} редактировать старые и вносить новые записи о приступах?", parse_mode='HTML', reply_markup=get_commiting_changing_editing_permission_kb(tpp_id))
    elif not trusted_person_info['permissions']['can_edit']:
        await message.answer(f"Вы хотите <b>разрешить</b> пользователю {trusted_person_info['trusted_user']['login']} редактировать старые и вносить новые записи о приступах?", parse_mode='HTML', reply_markup=get_commiting_changing_editing_permission_kb(tpp_id))


@control_panel_router.callback_query(F.data.startswith("tpchangeediting"))
async def process_commit_changing_editing_permission(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, answer, tpp_id = callback.data.split(':', 2)
    if answer == "yes":
        await orm_switch_trusted_profile_notify_edit_state(db, int(tpp_id), switch_edit=True)
        await callback.message.edit_text("Изменения прав сохранены.")
        await delete_redis_trusted_persons(callback.message.chat.id)
    else:
        await callback.message.edit_text("Изменения прав отменено.")
    await callback.answer()

@control_panel_router.message(F.text.startswith("/tpchangecanrecievenotify"))
async def process_change_getting_notification_permission(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    tpp_id = message.text.split('_', 1)[1]
    if not tpp_id.isnumeric():
        await message.answer("Неверный индекс записи.")
        return
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, message.chat.id)
    if int(tpp_id) not in [int(tp['permissions']['id']) for tp in trusted_persons]:
        await message.answer("Для вашего пользователя нет такой записи.")
        return
    trusted_person_info = find_trusted_record_by_id(trusted_persons, int(tpp_id))
    if trusted_person_info['permissions']['get_notification']:
        await message.answer(f"Вы хотите <b>запретить</b> пользователю {trusted_person_info['trusted_user']['login']} получать экстренные уведомления о приступах?", parse_mode='HTML', reply_markup=get_commiting_changing_notify_permission_kb(tpp_id))
    elif not trusted_person_info['permissions']['can_edit']:
        await message.answer(f"Вы хотите <b>разрешить</b> пользователю {trusted_person_info['trusted_user']['login']} получать экстренные уведомления о приступах?", parse_mode='HTML', reply_markup=get_commiting_changing_notify_permission_kb(tpp_id))

@control_panel_router.callback_query(F.data.startswith("tpchangegettingnotify"))
async def process_delete_trusted_person(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, answer, tpp_id = callback.data.split(':', 2)
    if answer == "yes":
        await orm_switch_trusted_profile_notify_edit_state(db, int(tpp_id), getting_notify=True)
        await callback.message.edit_text("Изменения прав сохранены.")
        await delete_redis_trusted_persons(callback.message.chat.id)
    else:
        await callback.message.edit_text("Изменения прав отменено.")
    await callback.answer()

@control_panel_router.message(F.text.startswith("/tpdelete"))
async def process_deleting_trusted_person(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    tpp_id = message.text.split('_', 1)[1]
    if not tpp_id.isnumeric():
        await message.answer("Неверный индекс записи.")
        return
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, message.chat.id)
    if int(tpp_id) not in [int(tp['permissions']['id']) for tp in trusted_persons]:
        await message.answer("Для вашего пользователя нет такой записи.")
        return
    await message.answer("Вы действительно хотите удалить доверенное лицо?", reply_markup=get_commiting_deleting_trusted_person_kb(tpp_id))

@control_panel_router.callback_query(F.data.startswith("tpdeleting"))
async def process_delete_trusted_person(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, answer, tpp_id = callback.data.split(':', 2)
    if answer == "yes":
        if answer == 'yes':
            res = await orm_delete_tursted_person(db, int(tpp_id))
            if res:
                await callback.message.edit_text("Доверенное лицо успешно удалено.")
                await delete_redis_trusted_persons(callback.message.chat.id)
            else:
                await callback.message.edit_text("Нет такой записи.")
    else:
        await callback.message.edit_text("Удаление доверенного лица отменено.")
    await callback.answer()