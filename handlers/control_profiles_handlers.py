from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.profiles_list_kb import get_profile_submenu_kb
from keyboards.medication_kb import get_medication_sumbenu

control_profiles_router = Router()

@control_profiles_router.callback_query(F.data == 'control_profiles')
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите действие: редактировать профиль, панель управления доверенными лицами, добавить доверенное лицо или импортировать/экспортировать данные",
        reply_markup=get_profile_submenu_kb()
    )
    await callback.answer()

@control_profiles_router.callback_query(F.data == 'medication')
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите действие: добавить курс препарата или изменить существующий курс",
        reply_markup=get_medication_sumbenu()
    )
    await callback.answer()
