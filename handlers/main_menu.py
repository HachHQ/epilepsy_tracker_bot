from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command


from database.db_init import SessionLocal
from database.models import User

from keyboards.menu_kb import get_main_menu_keyboard

from services.notification_queue import get_notification_queue

main_menu_router = Router()


@main_menu_router.message(Command(commands="menu"))
async def send_main_menu(message: Message):
    await message.answer(
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard()
    )

@main_menu_router.message(Command(commands='get_user'))
async def process_bold_command(message: Message):
    await message.answer(
        text='*Введите уникальный логин пользователя которого хотите сделать доверенным лицом*'
    )

@main_menu_router.message(F.text.startswith("admin."))
async def get_login_from_user(message: Message):
    text_fin = message.text.split(".")[1]
    print(text_fin)
    db = SessionLocal()
    try:
        existing_by_login = db.query(User).filter(User.login == text_fin).first()
        if not existing_by_login:
            await message.answer(text=f"Пользователь с логином '{text_fin}' не существует, попробуйте ввести другой.",
            parse_mode="HTML")
            return
        await message.answer(
            text=f"Вот данные пользователя {existing_by_login.login}: \n {existing_by_login.telegram_id} \n {existing_by_login.telegram_username} \n {existing_by_login.telegram_fullname} \n {existing_by_login.name} \n {existing_by_login.created_at} ",
            parse_mode="HTML"
        )
        print("Пользователь успешно найден")
        await get_notification_queue().send_notification(chat_id=existing_by_login.telegram_id, text=f"{existing_by_login.name}, вам перевели 1 000 000 ФПИ Банок")
        print("Пользователю успешно отправлено уведомление.")
    except InterruptedError as e:
        print(f"Ошибка создания пользователя: {e}")
        db.rollback()
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
    finally:
        db.close()



@main_menu_router.callback_query(F.data == "to_menu")
async def send_main_menu_callback(callback: CallbackQuery):
    await callback.message.answer(
        f"Вы находитесь в основном меню бота.\n"
        "Используйте кнопки для навигации.\n",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()