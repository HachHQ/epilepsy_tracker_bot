import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from matplotlib.cbook import CallbackRegistry
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.telegram.notification_queue import NotificationQueue, SosMassNotification
from i18n import t
from keyboards.notification_kb import get_choose_sos_notify_mode_kb
from services.redis_cache_data import get_cached_trusted_persons_agrigated_data

sos_router = Router()
logger = logging.getLogger(__name__)

@sos_router.callback_query(F.data == 'sos_notification')
async def process_ask_for_geoloc(callback: CallbackRegistry, state: FSMContext):
    await callback.message.answer(
        t("sos.ask_prompt"),
        reply_markup=get_choose_sos_notify_mode_kb(),
        parse_mode='HTML',
    )
    await callback.answer()


def get_sos_notify_message_with_args(tg_name, tg_username, location=None):
    username = f"@{tg_username}" if tg_username else ""
    return t(
        "sos.notify_template",
        tg_name=tg_name,
        username=username,
        location=location if location else t("sos.unknown_location"),
    )


def get_tr_usernames_of_user(tr_users):
    text = t("sos.sent_header") + "\n"
    for tr in tr_users:
        if tr['permissions']['get_notification']:
            username = tr['trusted_user']['telegram_username']
            fullname = tr['trusted_user']['telegram_fullname']
            text += f"{'@' + username if username is not None else fullname}\n"
    return text


@sos_router.callback_query(F.data.startswith('sos_notify_with_geo'))
async def process_send_sos_notify_to_trusted_persons(
    callback: CallbackRegistry,
    state: FSMContext,
    db: AsyncSession,
    notification_queue: NotificationQueue,
):
    first_name = callback.from_user.full_name
    username = callback.from_user.username if callback.from_user.username else t("sos.no_username")
    text = get_sos_notify_message_with_args(first_name, username)
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, callback.message.chat.id)
    unique = {}
    for tr in trusted_persons:
        try:
            if tr['permissions']['get_notification']:
                unique[tr['trusted_user']['id']] = tr['trusted_user']['telegram_id']
        except Exception:
            logger.exception("Failed to process trusted person entry: %s", tr)
    trusted_persons_tg_ids = list(unique.values())
    if len(trusted_persons_tg_ids) == 0:
        await callback.message.answer(t("sos.no_trusted_persons"))
    await callback.message.answer(get_tr_usernames_of_user(trusted_persons))
    await notification_queue.enqueue(SosMassNotification(trusted_persons_tg_ids, text))
    await callback.answer()
