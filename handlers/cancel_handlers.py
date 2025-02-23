from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, default_state
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter

from lexicon.lexicon import LEXICON_RU

cancel_router = Router()

@cancel_router.message(Command(commands="cancel"), ~StateFilter(default_state))
async def cancel_form(message: Message, state: FSMContext):
    await message.answer(LEXICON_RU['cancel_script'])
    await state.clear()

@cancel_router.message(Command(commands="cancel"), StateFilter(default_state))
async def cancel_outside_fsm(message: Message):
    await message.answer(LEXICON_RU['not_in_script'])

@cancel_router.callback_query(F.data == "cancel_fsm_script", ~StateFilter(default_state))
async def cancel_fsm_script(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(LEXICON_RU['cancel_script'])
    await state.clear()
    await callback.answer()

@cancel_router.callback_query(F.data == "cancel_fsm_script", StateFilter(default_state))
async def cancel_fsm_script(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(LEXICON_RU['not_in_script'])
    await state.clear()
    await callback.answer()