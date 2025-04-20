from aiogram import Bot
from aiogram.types import BotCommand

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/menu', description='Вызвать основное меню'),
        BotCommand(command='/graphs', description='Вызвать меню для графиков'),
        BotCommand(command='/stats', description='Вызвать меню для статистики'),
        BotCommand(command='/help', description='Узнать о возможностях бота'),
        BotCommand(command='/start', description='Начать работу с ботом'),
    ]
    await bot.set_my_commands(main_menu_commands)