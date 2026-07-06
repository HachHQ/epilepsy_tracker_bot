from aiogram import F, Router
from aiogram.types import CallbackQuery

from i18n import t
from keyboards.profiles_list_kb import get_profile_submenu_kb

control_profiles_router = Router()

@control_profiles_router.callback_query(F.data == 'control_profiles')
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        t("menu.control_profiles"),
        reply_markup=get_profile_submenu_kb()
    )
    await callback.answer()
