import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent
from aiogram.fsm.storage.redis import RedisStorage

from database.db_init import init_db
from database.redis_client import redis
from database.db_init import SessionLocal

from adapters.telegram.medication_reminders import schedule_notification_slots, scheduler
from services.retention_purge import schedule_retention_purge

from config_data.config import get_config, load_config

from handlers.account_handlers import account_router
from handlers.analytics_handlers import analytics_router
from handlers.journal_handlers import journal_router
from handlers.choose_profile_handlers import choose_profile_router
from handlers.import_export_handlers import import_export_router
from handlers.trusted_person_handlers import trusted_person_router
from handlers.profiles_pagination_handlers import pagination_router
from handlers.cancel_handlers import cancel_router
from handlers.start_message import start_message_router
from handlers.user_form import user_form_router
from handlers.profile_form import profile_form_router
from handlers.main_menu import main_menu_router
from handlers.seizures_handlers import seizures_router
from handlers.control_profiles_handlers import control_profiles_router
from handlers.medication_handlers import medication_router
from handlers.notification_handlers import notification_router
from handlers.sos_handlers import sos_router

from keyboards.set_menu import set_main_menu

from middleware.inner import NotificationMiddleware, DatabaseSessionMiddleware
from middleware.locale import LocaleMiddleware

from adapters.telegram.notification_queue import NotificationQueue
from i18n import set_locale, t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = get_config()

storage = RedisStorage(redis=redis)
# default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2)
telegram_proxy = os.getenv("TELEGRAM_PROXY")
if telegram_proxy:
    logger.info("Telegram API proxy enabled: %s", telegram_proxy)
    bot = Bot(config.tg_bot.token, session=AiohttpSession(proxy=telegram_proxy))
else:
    bot = Bot(config.tg_bot.token)
dp = Dispatcher(storage=storage)

@dp.error()
async def handle_errors(event: ErrorEvent, state: FSMContext):
    logger.error(
        "Unhandled update error: %s",
        event.exception,
        exc_info=(type(event.exception), event.exception, event.exception.__traceback__),
    )
    await state.clear()
    if event.update.message:
        set_locale("ru")
        await event.update.message.answer(t("common.generic_error"))

notification_queue = NotificationQueue(bot, redis, rate_limit=0.05)

async def main():
    await init_db()

    dp.update.middleware(NotificationMiddleware(notification_queue))
    dp.update.middleware(LocaleMiddleware())
    dp.update.middleware(DatabaseSessionMiddleware(SessionLocal))

    dp.include_router(cancel_router)
    dp.include_router(start_message_router)
    dp.include_router(main_menu_router)
    dp.include_router(sos_router)
    dp.include_router(trusted_person_router)
    dp.include_router(import_export_router)
    dp.include_router(analytics_router)
    dp.include_router(pagination_router)
    dp.include_router(choose_profile_router)
    dp.include_router(seizures_router)
    dp.include_router(journal_router)
    dp.include_router(control_profiles_router)
    dp.include_router(account_router)
    dp.include_router(user_form_router)
    dp.include_router(profile_form_router)
    dp.include_router(medication_router)
    dp.include_router(notification_router)

    schedule_notification_slots(notification_queue)
    schedule_retention_purge()
    scheduler.start()

    try:
        await notification_queue.start()
        await set_main_menu(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await notification_queue.stop()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())