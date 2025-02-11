from aiogram import Bot
from aiogram.types import BotCommand

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/start',
                   description='Начать работу с ботом / Заполнить анкету заново'),
        BotCommand(command='/menu',
                   description='Вызвать основное меню'),
        BotCommand(command='/help',
                   description='Узнать о возможностях бота'),
    ]
    await bot.set_my_commands(main_menu_commands)