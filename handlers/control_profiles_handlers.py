from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.profiles_list_kb import get_profile_submenu_kb

control_profiles_router = Router()

@control_profiles_router.callback_query(F.data == 'control_profiles')
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите действие: редактировать профиль, панель управления доверенными лицами или добавить доверенное лицо",
        reply_markup=get_profile_submenu_kb()
    )
    await callback.answer()
