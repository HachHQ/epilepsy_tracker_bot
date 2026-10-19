import logging
import os
from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.delivery import send_document_file
from handlers_logic.access_reply import deny_read_only
from handlers_logic.states_factories import GetExcelTableForm
from i18n import t
from services.profile_ref import ProfileRef
from services.redis_cache_data import get_cached_login
from services.to_excel import get_excel_template_path
from use_cases import import_export as import_export_use_cases

import_export_router = Router()
logger = logging.getLogger(__name__)


@import_export_router.callback_query(F.data == "export_data")
async def process_export_excel_data_by_profile(
    callback: CallbackQuery, db: AsyncSession, bot: Bot, current_profile: ProfileRef | None
):
    prof = current_profile
    if prof is None:
        await callback.message.answer(t("journal.select_profile_short"))
        await callback.answer()
        return
    file_path = await import_export_use_cases.export_profile_seizures_excel(
        db, prof.id
    )
    await send_document_file(bot, callback.message.chat.id, file_path)
    await callback.answer()


@import_export_router.callback_query(F.data == "import_data")
async def process_import_excel_data_by_profile(
    callback: CallbackQuery, state: FSMContext, bot: Bot, current_profile: ProfileRef | None
):
    if await deny_read_only(callback, current_profile):
        return
    await send_document_file(
        bot,
        callback.message.chat.id,
        get_excel_template_path(),
        caption=t("import.template_caption"),
        remove_after=False,
    )
    await callback.message.answer(t("import.download_template"))
    await state.set_state(GetExcelTableForm.get_xlsx_file)
    await callback.answer()


@import_export_router.message(F.document, StateFilter(GetExcelTableForm))
async def handle_excel_upload(
    message: Message,
    db: AsyncSession,
    state: FSMContext,
    bot: Bot,
    current_profile: ProfileRef | None,
):
    if not message.document.file_name.endswith(".xlsx"):
        await message.answer(t("import.xlsx_required"))
        return

    file_path = ""
    try:
        prof = current_profile
        login = await get_cached_login(db, message.chat.id)
        if await deny_read_only(message, prof):
            return
        if prof is None or login is None:
            await message.answer(t("journal.select_profile_short"))
            return
        file_id = str(uuid4())
        file_path = f"import_temp/{file_id}.xlsx"
        os.makedirs("import_temp", exist_ok=True)
        file = await bot.get_file(message.document.file_id)
        await bot.download_file(file.file_path, destination=file_path)
        result = await import_export_use_cases.import_seizures_from_excel(
            db,
            file_path=file_path,
            profile_id=prof.id,
            login=login,
            user_id=message.chat.id,
        )
        text = t(
            "import.import_complete",
            valid_count=result.success_count,
            failed_count=len(result.failed_rows),
        )
        await message.answer(text)
        if result.failed_rows:
            import pandas as pd

            df_failed = pd.DataFrame(result.failed_rows)
            failed_file_path = f"import_temp/{file_id}_errors.xlsx"
            df_failed.to_excel(failed_file_path, index=False)
            await message.answer_document(
                document=FSInputFile(failed_file_path),
                caption=t("import.failed_rows_caption"),
            )
            os.remove(failed_file_path)
    except Exception as exc:
        logger.exception("Excel import failed")
        await message.answer(t("import.file_processing_error", error=str(exc)))
    finally:
        await state.clear()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
