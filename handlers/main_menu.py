import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.anchor import drop_anchor, live_message
from adapters.telegram.ephemeral import send_notice
from i18n import t
from keyboards.menu_kb import get_main_menu_keyboard
from services.profile_ref import ProfileRef
from services.redis_cache_data import get_cached_login

logger = logging.getLogger(__name__)

main_menu_router = Router()

async def get_main_menu_text(
    session: AsyncSession, message: Message, curr_prof: ProfileRef | None
):
    lg = await get_cached_login(session, message.chat.id)
    text = t(
        "menu.main_status",
        login=lg if lg is not None else t("menu.login_not_registered"),
        profile=curr_prof.name if curr_prof is not None else t("menu.profile_not_selected"),
    )
    return text


async def show_main_menu(
    message: Message,
    db: AsyncSession,
    current_profile: ProfileRef | None,
    *,
    edit: bool = False,
) -> None:
    text = await get_main_menu_text(db, message, current_profile)
    markup = get_main_menu_keyboard()
    if edit:
        try:
            await message.edit_text(text, reply_markup=markup, parse_mode="MarkDownV2")
            return
        except TelegramBadRequest:
            logger.debug("Main menu message could not be edited, sending a new one")
    await message.answer(text, reply_markup=markup, parse_mode="MarkDownV2")


async def return_to_main_menu(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    current_profile: ProfileRef | None,
    *,
    notice: str,
) -> None:
    """Drop the scenario prompt and leave the main menu as the latest message."""
    await send_notice(message, notice, reply_markup=ReplyKeyboardRemove())
    await drop_anchor(message.bot, message.chat.id, state)
    await state.clear()
    await show_main_menu(message, db, current_profile)


@main_menu_router.message(Command(commands="menu"))
async def send_main_menu(
    message: Message, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    await state.clear()
    await show_main_menu(message, db, current_profile)


@main_menu_router.callback_query((F.data == "to_menu") | (F.data == "to_menu_edit"))
async def send_main_menu_callback(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_profile: ProfileRef | None
):
    message = live_message(callback.message)
    if message is None:
        await callback.answer()
        return
    edit = callback.data == "to_menu_edit"
    if not edit:
        await state.clear()
    await show_main_menu(message, db, current_profile, edit=edit)
    await callback.answer()
