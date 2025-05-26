import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent
from aiogram.fsm.storage.redis import RedisStorage

from database.db_init import init_db
from database.redis_client import redis
from database.db_init import SessionLocal

from config_data.config import load_config

from test_scripts.test1 import test_create_user

from handlers.analytics_handlers import analytics_router
from handlers.journal_handlers import journal_router
from handlers.choose_profile_handlers import choose_profile_router
from handlers.add_trusted_person_handlers import add_trusted_person_router
from handlers.profiles_pagination_handlers import pagination_router
from handlers.cancel_handlers import cancel_router
from handlers.start_message import start_message_router
from handlers.user_form import user_form_router
from handlers.profile_form import profile_form_router
from handlers.main_menu import main_menu_router
from handlers.seizures_handlers import seizures_router
from handlers.control_profiles_handlers import control_profiles_router

from keyboards.set_menu import set_main_menu

from middleware.inner import NotificationMiddleware, DatabaseSessionMiddleware

from services.notification_queue import NotificationQueue

config = load_config(".env")

storage = RedisStorage(redis=redis)
# default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2)
bot = Bot(config.tg_bot.token)
dp = Dispatcher(storage=storage)

@dp.error()
async def handle_errors(event: ErrorEvent, state: FSMContext):
    print(f"Произошла ошибка: {event.exception}")
    await state.clear()
    await event.update.message.answer("Что-то пошло не так. Попробуйте позже. Все сценарии отменены")

notification_queue = NotificationQueue(bot, redis, rate_limit=0.05)

async def main():
    await init_db()

    dp.update.middleware(NotificationMiddleware(notification_queue))
    dp.update.middleware(DatabaseSessionMiddleware(SessionLocal))

    dp.include_router(cancel_router)
    dp.include_router(start_message_router)
    dp.include_router(main_menu_router)
    dp.include_router(add_trusted_person_router)
    dp.include_router(analytics_router)
    dp.include_router(pagination_router)
    dp.include_router(choose_profile_router)
    dp.include_router(seizures_router)
    dp.include_router(journal_router)
    dp.include_router(control_profiles_router)
    dp.include_router(user_form_router)
    dp.include_router(profile_form_router)
    await notification_queue.start()
    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    await notification_queue.stop()

if __name__ == "__main__":
    asyncio.run(main())