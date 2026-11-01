import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from i18n import t
from keyboards.oferta_kb import get_accept_oferta_kb

logger = logging.getLogger(__name__)

OFERTA_PDF_PATH = Path(__file__).resolve().parents[2] / "assets" / "oferta.pdf"


async def send_oferta_document(bot: Bot, chat_id: int, *, with_accept_button: bool) -> None:
    if not OFERTA_PDF_PATH.is_file():
        logger.error("Oferta PDF is missing: %s", OFERTA_PDF_PATH)
        await bot.send_message(chat_id, t("start.oferta_file_missing"))
        return

    caption_key = "start.oferta_caption" if with_accept_button else "start.oferta_caption_accepted"
    await bot.send_document(
        chat_id,
        FSInputFile(OFERTA_PDF_PATH, filename="oferta.pdf"),
        caption=t(caption_key),
        reply_markup=get_accept_oferta_kb() if with_accept_button else None,
    )
