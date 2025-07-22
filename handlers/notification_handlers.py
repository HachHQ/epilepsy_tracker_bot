from ast import Call
from asyncio import eager_task_factory
from faulthandler import is_enabled
from mailbox import Message
import nt
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import StateFilter
from datetime import datetime

from database.orm_query import orm_create_new_notification, orm_delete_notification, orm_get_all_user_notifications, orm_get_notification_by_id, orm_update_notification_settings
from handlers.journal_handlers import NOTES_PER_PAGE
from services.redis_cache_data import get_cached_user_id_from_db
from services.validators import validate_time,validate_less_than_100
from handlers_logic.states_factories import NotificationForm
from keyboards.notification_kb import get_notify_sumbenu, get_cancel_kb, get_notify_pattern, get_notify_to_enable_kb, get_confirm_deleting_notify_kb
from keyboards.journal_kb import get_nav_btns_for_list
from services.medication_reminders import get_nearest_slot

notification_router = Router()

NOTES_PER_PAGE = 6

@notification_router.callback_query(F.data == 'notifications_control')
async def process_choosing_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите действие: \n- Добавть уведомление\n- Изменить настройки существующего уведомления (Управление)",
        reply_markup=get_notify_sumbenu()
    )
    await callback.answer()

@notification_router.callback_query(F.data == "add_notification")
async def process_add_medication(callback: CallbackQuery, state: FSMContext):
    validator_error = "Время должно иметь формат - 12:23 (час:минуты)."
    text = (
        "Напишите время в которое хотие получить уведомление. Система округлит его до ближайшей четверти часа, учтите это.\n\n"
        f"{validator_error}"
    )
    await state.set_state(NotificationForm.notify_time)
    await callback.message.answer(text, reply_markup=get_cancel_kb())
    await callback.answer()

@notification_router.message(StateFilter(NotificationForm.notify_time))
async def process_notification_time(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    validator_error = "Время должно иметь формат - 12:23 (час:минуты)."
    if validate_time(message.text):
        await state.update_data(notify_time=message.text)
        data = await state.get_data()
        mode = data.get("ntmode", "create")
        if mode == 'notification_edit_mode':
            nt_id=data['nt_id']
            user_id_db=data['user_id_db']
            formatted_time = get_nearest_slot(datetime.strptime(message.text, "%H:%M").time())
            await orm_update_notification_settings(db, int(user_id_db), int(nt_id), 'notify_time', formatted_time)
            await message.answer(f"Время уведомления обновлено: {message.text}")
            await state.clear()
            return
        text = (
            "Введите текст уведомления: \n\n"
            "Текст не может быть длиннее 100 символов."
        )
        await state.set_state(NotificationForm.note)
        await message.answer(text, reply_markup=get_cancel_kb())
    else:
        await message.answer(validator_error, reply_markup=get_cancel_kb())

@notification_router.message(StateFilter(NotificationForm.note))
async def process_notification_note(message: CallbackQuery, state: FSMContext, db: AsyncSession):
    validator_error = "Текст не может быть длиннее 100 символов."
    if validate_less_than_100(message.text):
        await state.update_data(note=message.text)
        data = await state.get_data()
        mode = data.get("ntmode", "create")
        if mode == 'notification_edit_mode':
            nt_id=data['nt_id']
            user_id_db=data['user_id_db']
            await orm_update_notification_settings(db, int(user_id_db), int(nt_id), 'note', message.text)
            await message.answer(f"Текст уведомления обновлен: {message.text}")
            await state.clear()
            return
        text = (
            "Выберите частоту уведмления:"
        )
        await state.set_state(NotificationForm.pattern)
        await message.answer(text, reply_markup=get_notify_pattern())
    else:
        await message.answer(validator_error, reply_markup=get_cancel_kb())

@notification_router.callback_query(F.data.startswith('notification_pattern'), StateFilter(NotificationForm.pattern))
async def process_notification_pattern_and_saving(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    notification_pattern = callback.data.split(':')[1]
    data = await state.get_data()
    if len(data) == 0:
        await callback.message.answer("Начните заполнение заново.")
    mode = data.get("ntmode", "create")
    if mode == 'notification_edit_mode':
        nt_id=data['nt_id']
        user_id_db=data['user_id_db']
        await orm_update_notification_settings(db, int(user_id_db), int(nt_id), 'pattern', notification_pattern)
        await callback.message.answer(f"Режим уведомления обновлен: {'Каждый день' if notification_pattern == 'daily' else 'Единожды'}")
        await state.clear()
        await callback.answer()
        return
    notify_time = data.get('notify_time', None)
    note = data.get('note', None)
    user_id = await get_cached_user_id_from_db(db, callback.message.chat.id)
    formatted_time = get_nearest_slot(datetime.strptime(notify_time, "%H:%M").time())
    await orm_create_new_notification(db, *[user_id, formatted_time, note, notification_pattern])
    if notification_pattern == 'daily':
        notification_pattern = 'Каждый день'
    elif notification_pattern == 'once':
        notification_pattern = 'Единожды'
    text = (
        "Уведомление создано\n\n"
        f"Время: {notify_time}\n"
        f"Заметка: {note}\n"
        f"Режим: {notification_pattern}"
    )
    await state.clear()
    await callback.message.answer(text)
    await callback.answer()

def display_notifications(user_notificatins, current_page):
    current_page = int(current_page)
    start_index = current_page * NOTES_PER_PAGE
    end_index = int(start_index) + NOTES_PER_PAGE
    user_nt_on_page = user_notificatins[start_index:end_index]
    text = ""
    for user_nt in user_nt_on_page:
        line = (
            f"🔔 - {str(user_nt.notify_time)[:5]} {'Каждый день' if user_nt.pattern == 'daily' else 'Единожды'} {"✅" if user_nt.is_enabled else "❌"} - /ntfyedit_{user_nt.id}\n\n"
        )
        text += line
    return text

@notification_router.callback_query(F.data == 'notification_control_panel')
async def process_notification_control_panel(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    user_id_db = await get_cached_user_id_from_db(db, callback.message.chat.id)
    user_notifications = await orm_get_all_user_notifications(db, user_id_db)
    if user_notifications is None:
        await callback.message.answer("У вас нет сохраненных уведомлений.")
    text = f"Ваши уведомления (Всего {len(user_notifications)})\n\n"
    text += display_notifications(user_notifications, 0)
    await callback.message.answer(text, parse_mode='HTML', reply_markup=get_nav_btns_for_list(len(user_notifications), NOTES_PER_PAGE, 0, 'user_notifications_journal'))
    await callback.answer()

@notification_router.callback_query(F.data.startswith('user_notifications_journal'))
async def process_pagination_of_notifys_list(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, page = callback.data.split(':', 1)
    user_id_db = await get_cached_user_id_from_db(db, callback.message.chat.id)
    user_notifications = await orm_get_all_user_notifications(db, user_id_db)
    if user_notifications is None:
        await callback.message.answer("У вас нет сохраненных уведомлений.")
    text = f"Ваши уведомления (Всего {len(user_notifications)})\n\n"
    text += display_notifications(user_notifications, page)
    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_nav_btns_for_list(len(user_notifications), NOTES_PER_PAGE, page, 'user_notifications_journal'))
    await callback.answer()

@notification_router.message(F.text.startswith('/ntfyedit'))
async def process_pagination_of_notifys_list(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    print(message.text)
    notify_id = message.text.split('_', 1)[1]
    user_id_db = await get_cached_user_id_from_db(db, message.chat.id)
    user_notification = await orm_get_notification_by_id(db, int(user_id_db), int(notify_id))
    if user_notification is None:
        await message.answer('Нет такой записи.')
        return
    text = (
        "Настройки уведомления\n\n"
        f"⏱️ Время: {str(user_notification.notify_time)[:5]} - /ntupdate_time_{user_notification.id}\n"
        f"🗒️ Заметка: {user_notification.note} - /ntupdate_note_{user_notification.id}\n"
        f"🔰 Режим: {'Каждый день' if user_notification.pattern == 'daily' else "Единожды"} - /ntupdate_pattern_{user_notification.id}\n"
        f"📣 Активно: {"✅" if user_notification.is_enabled else "❌"} - /ntupdate_enabled_{user_notification.id}\n"
        f"📌 Создано: {user_notification.created_at.date()}\n"
        f"🗑️ Удалить уведомление: - /ntdelete_{user_notification.id}"
    )
    await message.answer(text)

@notification_router.message(F.text.startswith('/ntupdate'))
async def process_editing_notify_settings(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, action, nt_id = message.text.split('_', 2)
    user_id_db = await get_cached_user_id_from_db(db, message.chat.id)
    user_notification = await orm_get_notification_by_id(db, int(user_id_db), int(nt_id))
    if user_notification is None:
        await message.answer('Нет такой записи.')
        return
    await state.update_data(ntmode="notification_edit_mode", nt_id=nt_id, user_id_db=user_id_db)
    if action == "time":
        validator_error = "Время должно иметь формат - 12:23 (час:минуты)."
        text = (
            "Напишите время в которое хотие получить уведомление. Система округлит его до ближайшей четверти часа, учтите это.\n\n"
            f"{validator_error}"
        )
        await message.answer(text)
        await state.set_state(NotificationForm.notify_time)
        sos =await state.get_state()
    elif action == "note":
        text = (
            "Введите текст уведомления: \n\n"
            "Текст не может быть длиннее 100 символов."
        )
        await message.answer(text)
        await state.set_state(NotificationForm.note)
    elif action == "pattern":
        text = (
            "Выберите частоту уведмления:"
        )
        await message.answer(text, reply_markup=get_notify_pattern())
        await state.set_state(NotificationForm.pattern)
    elif action == "enabled":
        if user_notification.is_enabled:
            await message.answer("Вы хотите отключить уведмление?", reply_markup=get_notify_to_enable_kb(nt_id, user_id_db, not user_notification.is_enabled))
        else:
            print(not user_notification.is_enabled)
            await message.answer("Вы хотите включить уведмление?", reply_markup=get_notify_to_enable_kb(nt_id, user_id_db, not user_notification.is_enabled))
    else:
        await message.answer("Нет такой команды.")

@notification_router.callback_query(F.data.startswith('nt_enabled_mode'))
async def process_edit_pattern_of_notification(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    _, answer, notify_id, user_id_db, enabled_mode = callback.data.split(':', 4)
    print(enabled_mode, type(enabled_mode))
    enabled_mode = enabled_mode.lower() == "true"
    print(enabled_mode, type(enabled_mode))
    if answer == 'yes':
        await orm_update_notification_settings(db, int(user_id_db), int(notify_id), 'is_enabled', enabled_mode)
        if enabled_mode:
            await callback.message.edit_text("Уведомление включено.")
        else:
            await callback.message.edit_text("Уведомление отключено.")
    else:
        await callback.message.edit_text("Изменение настроек уведомлений отменено.")
    await state.clear()
    await callback.answer()

@notification_router.message(F.text.startswith('/ntdelete'))
async def process_deleting_of_notify(message: Message, state: FSMContext, db: AsyncSession):
    print('ловим')
    await state.clear()
    notify_id = message.text.split('_', 1)[1]
    user_id_db = await get_cached_user_id_from_db(db, message.chat.id)
    user_notification = await orm_get_notification_by_id(db, int(user_id_db), int(notify_id))
    if user_notification is None:
        await message.answer('Нет такой записи.')
        return
    text = (
        "Вы действительно хотите удалить уведомление?"
    )
    await message.answer(text, reply_markup=get_confirm_deleting_notify_kb(notify_id, user_id_db))

@notification_router.callback_query(F.data.startswith("nt_delete"))
async def process_confirm_deleting_notify(callback: CallbackQuery, db: AsyncSession):
    _, answer, nt_id, user_id_db = callback.data.split(':', 3)
    if answer == 'yes':
        res = await orm_delete_notification(db, user_id_db, nt_id)
        if res:
            await callback.message.answer("Уведомление успешно удалено.")
        else:
            await callback.message.answer("Нет такой записи.")
    else:
        await callback.message.answer("Удаление уведомления отменено.")
    await callback.answer()

@notification_router.callback_query(F.data == 'confirm_getting_notification')
async def process_confirm_gettring_notify(callback: CallbackQuery):
    await callback.message.edit_text("Уведомление просмотрено ✅")