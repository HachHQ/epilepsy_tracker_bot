from aiogram import Bot
from aiogram.types import BotCommand

from i18n import set_locale, t


async def set_main_menu(bot: Bot):
    set_locale("ru")
    main_menu_commands = [
        BotCommand(command='/menu', description=t('bot_commands.menu')),
        BotCommand(command='/help', description=t('bot_commands.help')),
        BotCommand(command='/start', description=t('bot_commands.start')),
    ]
    await bot.set_my_commands(main_menu_commands)
