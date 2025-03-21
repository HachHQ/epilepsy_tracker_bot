import uuid
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta

from database.models import User, Profile, TrustedPersonProfiles, TrustedPersonRequest, RequestStatus
from lexicon.lexicon import LEXICON_RU
from services.redis_cache_data import get_cached_profiles_list, get_cached_login, set_cached_profiles_list
from services.notification_queue import NotificationQueue
from services.validators import validate_login_of_user_form
from keyboards.profiles_list_kb import get_paginated_profiles_kb
from keyboards.menu_kb import get_cancel_kb
from keyboards.trusted_user_kb import get_y_or_n_buttons_to_continue_process, get_y_or_n_buttons_to_finish_process

add_trusted_person_router = Router()

class TrustedPersonForm(StatesGroup):
    trusted_person_login = State()
    correct_trusted_person_login = State()
    selected_profile = State()
    confirm_transfer = State()


@add_trusted_person_router.callback_query(F.data == 'add_trusted')
async def process_input_trusted_person_login(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TrustedPersonForm.trusted_person_login)
    await callback.message.answer("Введите логин профиля пользователя, которому хотите доверить свой профиль: ", reply_markup=get_cancel_kb())
    await callback.answer()

@add_trusted_person_router.message(StateFilter(TrustedPersonForm.trusted_person_login))
async def process_search_trusted_person_by_login(message: Message, state: FSMContext, db: AsyncSession):
    if validate_login_of_user_form(message.text):
        login_redis = await get_cached_login(message.chat.id)
        await state.update_data(trusted_person_login=message.text)
        try:
            query = (
                select(User)
                .filter(User.login == message.text)
            )
            result = await db.execute(query)
            user = result.scalars().first()

            if user.login == login_redis:
                await message.answer("Нельзя стать доверенным лицом самого себя)")
                return

            if not user:
                await message.answer("Пользователь не найден")
                return
            await message.answer(f"Пользователь с логином {user.login} найден.\nЕго юзернейм в телеграме - {user.telegram_username}\nЕсли данные верны - нажмите 'Да', если нет - нажмите 'Нет'", reply_markup=get_y_or_n_buttons_to_continue_process())
            await state.set_state(TrustedPersonForm.correct_trusted_person_login)
        except Exception as e:
            print(f"Ошибка {e} при обращении к таблице users")
    else:
        await message.answer(LEXICON_RU['incorrect_login'], reply_markup=get_cancel_kb())

@add_trusted_person_router.callback_query(F.data == "trusted_person_correct", StateFilter(TrustedPersonForm.correct_trusted_person_login))
async def process_display_profile_for_transmitting(callback: CallbackQuery, state: FSMContext):
    profiles_redis = await get_cached_profiles_list(callback.message.chat.id)
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
        sender_login = await get_cached_login(callback.message.chat.id)

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
            await callback.message.answer("Начните заполнение сценарий добавления доверенного лица заново.")
            await state.clear()
            await callback.answer()
            return

        uuid_for_request = uuid.uuid4()

        new_request = TrustedPersonRequest(
            id = str(uuid_for_request),
            sender_id = user.id,
            recepient_id = recipient.id,
            transmitted_profile_id = int(data['transmitted_profile_id']),
            status = RequestStatus.PENDING
        )

        print(f"Новый запрос добавлен: {new_request}")
        await notification_queue.send_trusted_contact_request(chat_id=recipient.telegram_id,
                                              request_uuid=uuid_for_request,
                                              sender_login=sender_login,
                                              sender_id=user.id,
                                              transmitted_profile_id=int(data['transmitted_profile_id']),)
        db.add(new_request)
        await callback.message.answer("Запрос отправлен и будет активен в течение десяти минут.")
        await callback.answer()
        await state.clear()
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")

@add_trusted_person_router.callback_query(F.data == 'reject_transfer')
async def process_rejection(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Заполнение сценария заполнения передачи профиля доверенному лицу отменено.")
    await callback.answer()


@add_trusted_person_router.callback_query(F.data.startswith("p_conf") | F.data.startswith("n_conf"))
async def process_accept_trusted_person(callback: CallbackQuery, db: AsyncSession):
    action, uuid_request, transmitted_profile_id, sender_id = callback.data.split("|", 3)

    search_sender_result = await db.execute(select(User).filter(User.id == int(sender_id)))
    sender = search_sender_result.scalars().first()

    search_recepient_id_result = await db.execute(select(User).filter(User.telegram_id == callback.message.chat.id))
    recepient = search_recepient_id_result.scalars().first()

    search_request_result = await db.execute(select(TrustedPersonRequest).filter((TrustedPersonRequest.id == uuid_request) & (TrustedPersonRequest.sender_id == sender.id) & (TrustedPersonRequest.recepient_id == recepient.id)))
    request = search_request_result.scalars().first()

    print(request.created_at - request.expires_at)

    if not recepient:
        await callback.message.answer("Запрос не найден. Попросите пользователя отправить новый.")
        await callback.answer()
        return

    if request.status != RequestStatus.PENDING:
        await callback.message.answer("Запрос уже был обработан ранее.")
        await callback.answer()
        return

    if action == "p_conf":
        print(datetime.now(timezone.utc), request.expires_at)
        if datetime.now(timezone.utc) > request.expires_at:
            request.status = RequestStatus.EXPIRED
            await db.commit()
            await callback.message.answer("Время запроса истекло")
            await callback.answer()
            return
        request.status = RequestStatus.ACCEPTED
        await db.commit()
        new_trusted_person_profile = TrustedPersonProfiles(
            trusted_person_user_id = recepient.id,
            profile_owner_id = sender.id,
            profile_id = int(transmitted_profile_id),
        )
        db.add(new_trusted_person_profile)
        await db.commit()
        query = (
            select(Profile)
            .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
            .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
            .where(User.telegram_id == callback.message.chat.id)
        )
        profiles_result = await db.execute(query)
        profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
        await set_cached_profiles_list(callback.message.chat.id, "trusted", profiles)
        await callback.message.answer("Запрос подтвержден")
        await callback.answer()


    if action == "n_conf":
        request.status = RequestStatus.REJECTED
        await db.commit()
        await callback.message.answer("Запрос отклонен")
        await callback.answer()
    await callback.answer()
