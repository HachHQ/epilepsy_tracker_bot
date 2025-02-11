from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import Command, StateFilter
from datetime import datetime

from database.db_init import SessionLocal
from database.models import User

from services.validators import validate_login_of_user_form, validate_name_of_user_form

from keyboards.menu_kb import get_cancel_kb

user_form_router = Router()

class UserForm(StatesGroup):
    name = State()
    login = State()
    check_form = State()

# Хэндлер для команды /cancel (отмена анкеты)
@user_form_router.message(Command(commands="cancel"), ~StateFilter(default_state))
async def cancel_form(message: Message, state: FSMContext):
    await message.answer(
        "Вы отменили заполнение анкеты.\n"
        "Чтобы начать заново, отправьте команду /start."

    )
    # Сбрасываем состояние и очищаем данные FSM
    await state.clear()

# Хэндлер для команды /cancel вне состояний (по умолчанию)
@user_form_router.message(Command(commands="cancel"), StateFilter(default_state))
async def cancel_outside_fsm(message: Message):
    await message.answer(
        "Вы не находитесь в процессе заполнения анкеты.\n"
        "Чтобы начать заполнение, используйте команду /start.",

    )

@user_form_router.callback_query(F.data == "cancel_fsm_script", ~StateFilter(default_state))
async def cancel_fsm_script(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Вы отменили заполнение анкеты, чтобы начать заново, отправьте команду /start")
    await state.clear()
    await callback.answer()

@user_form_router.callback_query(F.data == "submit_welcome_msg")
async def start_form(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите свое имя:", reply_markup=get_cancel_kb())
    await state.set_state(UserForm.name)
    await callback.answer()

# Хэндлер для ввода имени
@user_form_router.message(StateFilter(UserForm.name))
async def process_name(message: Message, state: FSMContext):
    # Сохраняем имя пользователя
    if validate_name_of_user_form(message.text):
        print("Имя валидно")
        await state.update_data(name=message.text)
    # Спрашиваем логин
        await message.answer("Введите ваш уникальный логин:", reply_markup=get_cancel_kb())
    # Переводим в состояние UserForm.login
        await state.set_state(UserForm.login)

    else:
        await message.answer("Имя должно иметь длину от 1 до 20 символов, и использовать только буквы русского или английского алфавита", reply_markup=get_cancel_kb())
        return

@user_form_router.message(StateFilter(UserForm.login))
async def process_login(message: Message, state: FSMContext):
    if validate_login_of_user_form(message.text):
        print("Логин валиден")
        await state.update_data(login=message.text)

        data = await state.get_data()
        print(f"Полученные данные: {data}")
        db = SessionLocal()
        try:
            # Проверяем, существует ли пользователь с таким логином
            existing_login = db.query(User).filter(User.login == data["login"]).first()
            existing_tgid = db.query(User).filter(User.telegram_id == message.chat.id).first()

            if existing_tgid or existing_login:
                await message.answer(f"Пользователь с логином '{data['login']}' уже существует, попробуйте ввести другой.", reply_markup=get_cancel_kb())
                return

            new_user = User(
                telegram_id=message.chat.id,
                telegram_username=message.from_user.username,
                telegram_fullname=message.from_user.full_name,
                name=data["name"],  # Убедитесь, что доступ через ключи корректен
                login=data["login"],  # Убедитесь, что доступ через ключи корректен
                created_at=datetime.utcnow()
            )

            print(f"Создается пользователь: {new_user}")

            db.add(new_user)
            db.commit()

            next_to_profile_form_kb_bd = InlineKeyboardBuilder()
            next_to_profile_form_kb_bd.button(
                text="Да",
                callback_data="to_filling_profile_form"
            )
            next_to_profile_form_kb_bd.button(
                text="Нет",
                callback_data="to_menu"
            )

            await message.answer(
            f"Анкета заполнена!\nИмя: <b>{data['name']}</b>\nЛогин: <b>{data['login']}</b>\n\n"
            f"Если хотите изменить данные, отправьте команду /start, чтобы заполнить анкету заново.",
            parse_mode='HTML'
            )
            await message.answer(
                    "Хотите ли вы создать свой личный профиль?\n"
                    "Для этого потребуется ввести данные о виде эпилепсии, лечении и еще кое о чём.\n"
                    "Ботом можно пользоваться и без профиля, но тогда вы сможете только следить за состоянием тех людей, котороые добавлены в ваш список доверенных лиц.\n"
                    "А с личным профилем вы сможете заполнять собственный журнал.",
                    reply_markup=next_to_profile_form_kb_bd.as_markup()
            )

            print("Пользователь успешно создан.")
        except InterruptedError as e:
            print(f"Ошибка создания пользователя: {e}")
            db.rollback()
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
        finally:
            db.close()

        await state.clear()
    else:
        await message.answer("Логин должен иметь длину от 1 до 20 символов, использовать буквы русского или английского алфавита, но допускаются сиволы - '.' '_' '-'", reply_markup=get_cancel_kb())

