from aiogram import Router, F
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from matplotlib.cbook import CallbackRegistry
from sqlalchemy.ext.asyncio import AsyncSession

from handlers_logic.states_factories import SosForm
from keyboards.notification_kb import get_choose_sos_notify_mode_kb
from keyboards.profile_form_kb import get_geolocation_for_timezone_kb
from lexicon.lexicon import LEXICON_RU
from services.notification_queue import NotificationQueue, SosMassNotification
from services.redis_cache_data import get_cached_trusted_persons_agrigated_data

sos_router = Router()

@sos_router.callback_query(F.data == 'sos_notification')
async def process_ask_for_geoloc(callback: CallbackRegistry, state: FSMContext):
    await callback.message.answer("Нажмите на кнопку 'Отправить уведомления', чтобы разослать предупреждение об ухудшении вашего состояния доверенным лицам."
                         , reply_markup=get_choose_sos_notify_mode_kb(), parse_mode='HTML')
    #await state.set_state(SosForm.geolocation)
    await callback.answer()

def get_sos_notify_message_with_args(tg_name, tg_username, location = None):
    text = (
        f"⚠️ Внимание: пользователь {tg_name} сообщил о приступе эпилепсии.\n"
        f"Его юзернейм в телеграмме - {'@'+tg_username if tg_username else ''}\n"
        f"📌 Расположение: {location if location else "Неизвестно"}\n\n"
        "🔽 Рекомендуемые действия:\n"
        " - Свяжитесь с ним/ней, если это возможно.\n"
        " - Убедитесь, что он/она находится в безопасном положении (на боку, подложить что-то мягкое под голову).\n"
        " - Не удерживайте человека, не кладите предметы в рот.\n"
        " - Если приступ длится дольше 5 минут — вызывайте скорую: 103.\n\n"
        "🧠 Дополнительно: после приступа человек может быть дезориентирован. Оставайтесь с ним/ней, пока состояние не улучшится."
    )
    return text

def get_tr_usernames_of_user(tr_users):
    text = (
        "Доверенным лицам высланы уведомления: \n"
    )
    for tr in tr_users:
        if tr['permissions']['get_notification']:
                text += f"{'@'+tr['trusted_user']['telegram_username'] if tr['trusted_user']['telegram_username'] is not None else tr['trusted_user']['telegram_fullname']}\n"
    return text

@sos_router.callback_query(F.data.startswith('sos_notify_with_geo'))
async def process_send_sos_notify_to_trusted_persons(callback: CallbackRegistry, state: FSMContext, db: AsyncSession, notification_queue: NotificationQueue):
    first_name = callback.from_user.full_name
    username = callback.from_user.username if callback.from_user.username else "нет username"
    text = get_sos_notify_message_with_args(first_name, username)
    trusted_persons = await get_cached_trusted_persons_agrigated_data(db, callback.message.chat.id)
    unique = {}
    for tr in trusted_persons:
        try:
            if tr['permissions']['get_notification']:
                unique[tr['trusted_user']['id']] = tr['trusted_user']['telegram_id']
        except Exception as e:
            print(f"❌ Ошибка при обработке записи {tr}: {e}")
    trusted_persons_tg_ids = list(unique.values())
    if len(trusted_persons_tg_ids) == 0:
        await callback.message.answer("У вас нет доверенных лиц, которым вы разрешили получать уведомления.")
    await callback.message.answer(get_tr_usernames_of_user(trusted_persons))
    await notification_queue.enqueue(SosMassNotification(trusted_persons_tg_ids, text))
    await callback.answer()


#@sos_router.location()