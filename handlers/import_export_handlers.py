import logging
import os
from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.delivery import send_document_file
from handlers_logic.states_factories import GetExcelTableForm
from i18n import t
from services.redis_cache_data import get_cached_current_profile, get_cached_login
from services.to_excel import (
    build_seizures_excel,
    get_excel_template_path,
    import_seizures_from_xlsx,
)

import_export_router = Router()
logger = logging.getLogger(__name__)


@import_export_router.callback_query(F.data == "export_data")
async def process_export_excel_data_by_profile(callback: CallbackQuery, db: AsyncSession, bot: Bot):
    prof = await get_cached_current_profile(db, callback.message.chat.id)
    file_path = await build_seizures_excel(int(prof.split("|")[0]), db)
    await send_document_file(bot, callback.message.chat.id, file_path)
    await callback.answer()


@import_export_router.callback_query(F.data == "import_data")
async def process_import_excel_data_by_profile(callback: CallbackQuery, state: FSMContext, bot: Bot):
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
async def handle_excel_upload(message: Message, db: AsyncSession, state: FSMContext, bot: Bot):
    if not message.document.file_name.endswith(".xlsx"):
        await message.answer(t("import.xlsx_required"))
        return

    file_path = ""
    try:
        prof = await get_cached_current_profile(db, message.chat.id)
        login = await get_cached_login(db, message.chat.id)
        file_id = str(uuid4())
        file_path = f"import_temp/{file_id}.xlsx"
        os.makedirs("import_temp", exist_ok=True)
        file = await bot.get_file(message.document.file_id)
        await bot.download_file(file.file_path, destination=file_path)
        valid_count, failed_rows = await import_seizures_from_xlsx(
            file_path,
            db=db,
            profile_id=int(prof.split("|")[0]),
            login=login,
        )
        text = t("import.import_complete", valid_count=valid_count, failed_count=len(failed_rows))
        await message.answer(text)
        if failed_rows:
            import pandas as pd

            df_failed = pd.DataFrame(failed_rows)
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
