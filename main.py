import asyncio
from aiogram import Bot, Dispatcher, types, F
# from aiogram.client.default import DefaultBotProperties
# from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.filters import Command

import requests

from database.db_init import init_db
from database.redis_client import redis

from config_data.config import load_config

from test_scripts.test1 import test_create_user

from handlers.cancel_handlers import cancel_router
from handlers.start_message import start_message_router
from handlers.user_form import user_form_router
from handlers.profile_form import profile_form_router
from handlers.main_menu import main_menu_router

from keyboards.set_menu import set_main_menu

from middleware.inner import NotificationMiddleware

from services.notification_queue import NotificationQueue

config = load_config(".env")


storage = RedisStorage(redis=redis)
# default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2)
bot = Bot(config.tg_bot.token)
dp = Dispatcher(storage=storage)

notification_queue = NotificationQueue(bot, redis, rate_limit=0.05)

async def main():
    init_db()

    dp.update.middleware(NotificationMiddleware(notification_queue))

    dp.include_router(cancel_router)
    dp.include_router(start_message_router)
    dp.include_router(main_menu_router)
    dp.include_router(user_form_router)
    dp.include_router(profile_form_router)
    await notification_queue.start()
    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    await notification_queue.stop()

if __name__ == "__main__":
    asyncio.run(main())