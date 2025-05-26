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
from database.redis_query import set_redis_cached_profiles_list, set_redis_sending_timeout_ten_min, get_redis_sending_timeout_ten_min
from database.orm_query import orm_update_list_of_trusted_profiles, orm_get_user_by_login
from lexicon.lexicon import LEXICON_RU
from services.redis_cache_data import get_cached_profiles_list, get_cached_login
from services.notification_queue import NotificationQueue
from services.validators import validate_login_of_user_form
from services.hmac_encrypt import unpack_callback_data
from keyboards.profiles_list_kb import get_paginated_profiles_kb
from keyboards.menu_kb import get_cancel_kb
from keyboards.trusted_user_kb import get_y_or_n_buttons_to_continue_process, get_y_or_n_buttons_to_finish_process

add_trusted_person_router = Router()

@add_trusted_person_router.callback_query(F.data == 'add_trusted')
async def process_input_trusted_person_login(callback: CallbackQuery, state: FSMContext):
    timeout_check = await get_redis_sending_timeout_ten_min(callback.message.chat.id)
    if timeout_check is not None:
        await callback.message.answer("Запрос на добавление доверенного лица можно отправлять раз в 10 минут")
        return
    await state.set_state(TrustedPersonForm.trusted_person_login)
    await callback.message.answer("Введите логин профиля пользователя, которому хотите доверить свой профиль: ", reply_markup=get_cancel_kb())
    await callback.answer()

@add_trusted_person_router.message(StateFilter(TrustedPersonForm.trusted_person_login))
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

@add_trusted_person_router.callback_query(F.data == "trusted_person_correct", StateFilter(TrustedPersonForm.correct_trusted_person_login), UserOwnProfilesListExist())
async def process_display_profile_for_transmitting(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    profiles_redis = await get_cached_profiles_list(db, callback.message.chat.id)
    await callback.message.answer("Выберите профиль, которым хотите поделиться: ", reply_markup=get_paginated_profiles_kb(profiles_redis, to_share=True))
    await state.set_state(TrustedPersonForm.selected_profile)
    await callback.answer()

@add_trusted_person_router.callback_query((F.data.startswith('select_profile')) & (F.data.endswith('|share')), StateFilter(TrustedPersonForm.selected_profile))
async def process_submitting_profile_to_share(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    _, profile_id, profile_name_raw = callback.data.split(':', 2)
    profile_name = profile_name_raw.split('|', 1)[0]
    await state.update_data(transmitted_profile_id=profile_id)
    await state.update_data(transmitted_profile_name=profile_name)
    await callback.message.answer(f"Доверить данные вашего профиля {profile_name} пользователю {data['trusted_person_login']}?", reply_markup=get_y_or_n_buttons_to_finish_process())
    await state.set_state(TrustedPersonForm.confirm_transfer)
    await callback.answer()

@add_trusted_person_router.callback_query(F.data == 'confirm_transfer', StateFilter(TrustedPersonForm.confirm_transfer))
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

@add_trusted_person_router.callback_query(F.data == 'reject_transfer')
async def process_rejection(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Заполнение сценария заполнения передачи профиля доверенному лицу отменено.")
    await callback.answer()


@add_trusted_person_router.callback_query(F.data.startswith("p_conf") | F.data.startswith("n_conf"))
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
