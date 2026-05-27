# import asyncio
# from aiogram import Bot, Dispatcher
# from aiogram.fsm.context import FSMContext
# from aiogram.types import ErrorEvent
# from aiogram.fsm.storage.redis import RedisStorage

# from database.db_init import init_db
# from database.redis_client import redis
# from database.db_init import SessionLocal

# from services.medication_reminders import schedule_notification_slots, scheduler, start_workers

# from config_data.config import load_config

# from test_scripts.test1 import test_create_user

# from handlers.analytics_handlers import analytics_router
# from handlers.journal_handlers import journal_router
# from handlers.choose_profile_handlers import choose_profile_router
# from handlers.control_panel_handlers import control_panel_router
# from handlers.profiles_pagination_handlers import pagination_router
# from handlers.cancel_handlers import cancel_router
# from handlers.start_message import start_message_router
# from handlers.user_form import user_form_router
# from handlers.profile_form import profile_form_router
# from handlers.main_menu import main_menu_router
# from handlers.seizures_handlers import seizures_router
# from handlers.control_profiles_handlers import control_profiles_router
# from handlers.medication_handlers import medication_router
# from handlers.notification_handlers import notification_router
# from handlers.sos_handlers import sos_router

# from keyboards.set_menu import set_main_menu

# from middleware.inner import NotificationMiddleware, DatabaseSessionMiddleware

# from services.notification_queue import NotificationQueue


# config = load_config(".env")

# storage = RedisStorage(redis=redis)
# # default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2)
# bot = Bot(config.tg_bot.token)
# dp = Dispatcher(storage=storage)

# @dp.error()
# async def handle_errors(event: ErrorEvent, state: FSMContext):
#     print(f"Произошла ошибка: {event.exception}")
#     await state.clear()
#     await event.update.message.answer("Что-то пошло не так. Попробуйте позже. Все сценарии отменены")

# notification_queue = NotificationQueue(bot, redis, rate_limit=0.05)

# async def main():
#     await init_db()

#     dp.update.middleware(NotificationMiddleware(notification_queue))
#     dp.update.middleware(DatabaseSessionMiddleware(SessionLocal))

#     dp.include_router(cancel_router)
#     dp.include_router(start_message_router)
#     dp.include_router(main_menu_router)
#     dp.include_router(sos_router)
#     dp.include_router(control_panel_router)
#     dp.include_router(analytics_router)
#     dp.include_router(pagination_router)
#     dp.include_router(choose_profile_router)
#     dp.include_router(seizures_router)
#     dp.include_router(journal_router)
#     dp.include_router(control_profiles_router)
#     dp.include_router(user_form_router)
#     dp.include_router(profile_form_router)
#     dp.include_router(medication_router)
#     dp.include_router(notification_router)

#     schedule_notification_slots()
#     scheduler.start()
#     await start_workers(bot)

#     await notification_queue.start()
#     await set_main_menu(bot)
#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)
#     await notification_queue.stop()

# if __name__ == "__main__":
#     asyncio.run(main())

import logging
import sys
import asyncio

from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Импорты базы данных и редиса
from database.db_init import init_db
from database.redis_client import redis
from database.db_init import SessionLocal

# Импорты сервисов
from services.medication_reminders import schedule_notification_slots, scheduler, start_workers
from services.notification_queue import NotificationQueue

# Конфиг
from config_data.config import load_config
from keyboards.set_menu import set_main_menu

# Импорты роутеров
from handlers.analytics_handlers import analytics_router
from handlers.journal_handlers import journal_router
from handlers.choose_profile_handlers import choose_profile_router
from handlers.control_panel_handlers import control_panel_router
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

# Мидлвари
from middleware.inner import NotificationMiddleware, DatabaseSessionMiddleware

# --- КОНФИГУРАЦИЯ ВЕБХУКА ---
# В продакшене эти данные лучше брать из config (env)
# Ваш публичный домен (должен быть https)
WEB_SERVER_HOST = "127.0.0.1" # Слушаем все интерфейсы
WEB_SERVER_PORT = 5000      # Порт, который будет слушать aiohttp

# URL вашего сервера, куда Telegram будет слать запросы
# Например: https://mydomain.com
BASE_WEBHOOK_URL = "https://qcrtm-128-204-67-255.a.free.pinggy.link"
# Путь, по которому стучится телеграм (можно использовать токен для уникальности)
WEBHOOK_PATH = f"/webhook/bot"

config = load_config(".env")

# Инициализация бота и диспетчера
storage = RedisStorage(redis=redis)
bot = Bot(config.tg_bot.token)
dp = Dispatcher(storage=storage)

# Инициализация очереди
notification_queue = NotificationQueue(bot, redis, rate_limit=0.05)

@dp.error()
async def handle_errors(event: ErrorEvent, state: FSMContext):
    logging.error(f"Произошла ошибка: {event.exception}", exc_info=True)
    # await state.clear() # Осторожнее с этим, может сбрасывать состояние в неподходящий момент
    try:
        if event.update.message:
            await event.update.message.answer("Что-то пошло не так. Попробуйте позже.")
    except:
        pass


# --- ФУНКЦИЯ ЗАПУСКА (ON_STARTUP) ---
async def on_startup(bot: Bot):
    print("Bot starting up...")

    # 1. Инициализация БД
    await init_db()

    # 2. Планировщики (APScheduler)
    schedule_notification_slots()
    if not scheduler.running:
        scheduler.start()

    # 3. Воркеры и фоновые задачи
    # Важно: start_workers и notification_queue.start не должны блокировать цикл
    # Если они написаны как бесконечные циклы (while True), их нужно запускать через create_task
    asyncio.create_task(start_workers(bot))
    asyncio.create_task(notification_queue.start())

    # 4. Установка меню
    await set_main_menu(bot)

    # 5. Установка вебхука
    # drop_pending_updates=True сбросит старые сообщения, накопившиеся пока бот лежал
    await bot.set_webhook(
        f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
        drop_pending_updates=True
    )
    print(f"Webhook set to {BASE_WEBHOOK_URL}{WEBHOOK_PATH}")


# --- ФУНКЦИЯ ОСТАНОВКИ (ON_SHUTDOWN) ---
async def on_shutdown(bot: Bot):
    print("Bot shutting down...")

    # 1. Удаляем вебхук (опционально, но полезно при переключении обратно на поллинг)
    # await bot.delete_webhook()

    # 2. Останавливаем очередь
    await notification_queue.stop()

    # 3. Останавливаем планировщик
    if scheduler.running:
        scheduler.shutdown()

    # 4. Закрываем соединения
    # await redis.close() # Если нужно явно закрывать
    print("Bot stopped.")


def main():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Регистрация мидлварей
    dp.update.middleware(NotificationMiddleware(notification_queue))
    dp.update.middleware(DatabaseSessionMiddleware(SessionLocal))

    # Регистрация роутеров
    dp.include_router(cancel_router)
    dp.include_router(start_message_router)
    dp.include_router(main_menu_router)
    dp.include_router(sos_router)
    dp.include_router(control_panel_router)
    dp.include_router(analytics_router)
    dp.include_router(pagination_router)
    dp.include_router(choose_profile_router)
    dp.include_router(seizures_router)
    dp.include_router(journal_router)
    dp.include_router(control_profiles_router)
    dp.include_router(user_form_router)
    dp.include_router(profile_form_router)
    dp.include_router(medication_router)
    dp.include_router(notification_router)

    # Регистрация событий старта и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Создание веб-приложения aiohttp
    app = web.Application()

    # Создание обработчика запросов от Telegram
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        # secret_token="my-secret-token" # Рекомендуется для безопасности, нужно указать и в set_webhook
    )

    # Регистрация обработчика по пути вебхука
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Настройка приложения (связывает бота, диспетчер и app)
    setup_application(app, dp, bot=bot)

    # Запуск веб-сервера
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    main()