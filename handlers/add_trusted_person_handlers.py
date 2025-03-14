import uuid
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.models import User, Profile, TrustedPersonProfiles, TrustedPersonRequest, RequestStatus
from lexicon.lexicon import LEXICON_RU
from services.redis_cache_data import get_cached_profiles_list, get_cached_login
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
        await state.update_data(trusted_person_login=message.text)
        try:
            query = (
                select(User)
                .filter(User.login == message.text)
            )
            result = await db.execute(query)
            user = result.scalars().first()
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

        uuid_for_request = uuid.uuid4()

        new_request = TrustedPersonRequest(
            id = str(uuid_for_request),
            sender_id = user.id,
            recepient_id = recipient.id,
            transmitted_profile_id = data['transmitted_profile_id'],
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
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")

@add_trusted_person_router.callback_query(F.data == 'reject_transfer')
async def process_rejection(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Заполнение сценария заполнения передачи профиля доверенному лицу отменено.")
    await callback.answer()