from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.delivery import show_seizure_from_model
from config_data.pagination import JOURNAL_NOTES_PER_PAGE as NOTES_PER_PAGE
from filters.correct_commands import ProfileIsSetCb
from handlers_logic.seizure_form import start_seizure_field_edit
from i18n import t
from keyboards.journal_kb import (
    get_delete_seizure_note_kb,
    get_journal_nav_kb,
    get_nav_btns_for_list,
)
from services.redis_cache_data import get_cached_current_profile, get_cached_login
from use_cases.seizures import (
    delete_seizure_record,
    get_journal_seizure,
    list_journal_seizures,
    parse_current_profile,
)

journal_router = Router()


def _sort_seizures_by_datetime(seizures):
    def get_datetime(item):
        date_str = item.date
        if hasattr(item, "time") and item.time:
            return datetime.strptime(f"{date_str} {item.time}", "%Y-%m-%d %H:%M")
        return datetime.strptime(date_str, "%Y-%m-%d")

    return sorted(seizures, key=get_datetime, reverse=True)


def display_seizure_notes(seizures, current_page, login):
    seizures_sorted = _sort_seizures_by_datetime(seizures)
    current_page = int(current_page)
    start_index = current_page * NOTES_PER_PAGE
    end_index = start_index + NOTES_PER_PAGE
    text = ""
    for seizure in seizures_sorted[start_index:end_index]:
        creator = (
            seizure.creator_login + " "
            if seizure.creator_login is not None and seizure.creator_login != login
            else ""
        )
        time_part = seizure.time + " " if seizure.time is not None else ""
        text += t(
            "journal.list_item",
            date=seizure.date,
            time=time_part,
            creator=creator,
            id=seizure.id,
        )
    return text


@journal_router.callback_query(F.data == "seizure_data")
async def process_journal_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(t("journal.menu"), reply_markup=get_journal_nav_kb())


@journal_router.callback_query(F.data == "journal", ProfileIsSetCb())
async def get_list_of_seizures(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    login = await get_cached_login(db, callback.message.chat.id)
    current_profile = await get_cached_current_profile(db, callback.message.chat.id)
    if current_profile is None:
        await callback.message.answer(t("journal.select_profile"))
        return
    profile_id, profile_name = parse_current_profile(current_profile)
    seizures = await list_journal_seizures(db, profile_id)
    if not seizures:
        await callback.message.answer(
            t("journal.no_seizures", profile_name=profile_name),
            parse_mode="MarkDownV2",
        )
        await callback.answer()
        return
    text = t("journal.seizures_list_header", profile_name=profile_name)
    text += display_seizure_notes(seizures, 0, login)
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_nav_btns_for_list(len(seizures), NOTES_PER_PAGE, 0, "journal_page"),
    )
    await callback.answer()


@journal_router.callback_query(F.data.startswith("journal_page"))
async def process_pagination_of_seizures_list(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    login = await get_cached_login(db, callback.message.chat.id)
    _, page = callback.data.split(":", 1)
    current_profile = await get_cached_current_profile(db, callback.message.chat.id)
    profile_id, profile_name = parse_current_profile(current_profile)
    seizures = await list_journal_seizures(db, profile_id)
    text = t("journal.seizures_list_header", profile_name=profile_name)
    text += display_seizure_notes(seizures, int(page), login)
    await callback.message.edit_text(
        text,
        reply_markup=get_nav_btns_for_list(len(seizures), NOTES_PER_PAGE, int(page), "journal_page"),
        parse_mode="HTML",
    )


@journal_router.message(F.text.startswith("/show"))
async def get_detailed_info_about_seizure(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    await state.clear()
    seizure_id = message.text.split("_", 1)[1]
    if not seizure_id.isnumeric():
        await message.answer(t("journal.invalid_index"))
        return
    current_profile = await get_cached_current_profile(db, message.chat.id)
    if current_profile is None:
        await message.answer(t("journal.select_profile_short"))
        return
    profile_id, profile_name = parse_current_profile(current_profile)
    seizure = await get_journal_seizure(db, seizure_id=int(seizure_id), profile_id=profile_id)
    if not seizure:
        await message.answer(t("journal.record_not_found_for_profile", profile_name=profile_name))
        return
    await show_seizure_from_model(bot, message, seizure, profile_name)


@journal_router.message(F.text.startswith("/sjedit"))
async def show_edit_options(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    await state.clear()
    seizure_id = int(message.text.split("_", 1)[1])
    current_profile = await get_cached_current_profile(db, message.chat.id)
    profile_id, profile_name = parse_current_profile(current_profile)
    seizure = await get_journal_seizure(db, seizure_id=seizure_id, profile_id=profile_id)
    if not seizure:
        await message.answer(t("journal.record_not_found"))
        return
    await show_seizure_from_model(bot, message, seizure, profile_name, edit_mode=True)


@journal_router.message(F.text.startswith("/update"))
async def get_seizure_info_to_edit(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, action, seizure_id = message.text.split("_", 2)
    current_profile = await get_cached_current_profile(db, message.chat.id)
    profile_id, _ = parse_current_profile(current_profile)
    await start_seizure_field_edit(
        message,
        state,
        db,
        action=action,
        seizure_id=int(seizure_id),
        profile_id=profile_id,
    )


@journal_router.message(F.text.startswith("/delete"))
async def delete_seizure(message: Message, db: AsyncSession):
    seizure_id = int(message.text.split("_", 1)[1])
    current_profile = await get_cached_current_profile(db, message.chat.id)
    if current_profile is None:
        await message.answer(t("journal.select_profile_short"))
        return
    await message.answer(t("journal.delete_confirm"), reply_markup=get_delete_seizure_note_kb(seizure_id))


@journal_router.callback_query(F.data.startswith("delete_seizure_note"))
async def process_delete_seizure_note(callback: CallbackQuery, db: AsyncSession):
    _, answer, seizure_id = callback.data.split(":", 2)
    current_profile = await get_cached_current_profile(db, callback.message.chat.id)
    if current_profile is None:
        await callback.message.answer(t("journal.select_profile_short"))
        await callback.answer()
        return
    if answer == "yes":
        profile_id, _ = parse_current_profile(current_profile)
        deleted = await delete_seizure_record(
            db,
            user_id=callback.message.chat.id,
            profile_id=profile_id,
            seizure_id=int(seizure_id),
        )
        if deleted:
            await callback.message.edit_text(t("journal.delete_success"))
        else:
            await callback.message.edit_text(t("journal.delete_not_found"))
    else:
        await callback.message.edit_text(t("journal.delete_cancelled"))
    await callback.answer()
