from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adapters.telegram.notification_queue import (
    MedicationReminderNotification,
    NotificationQueue,
)


@pytest.mark.asyncio
async def test_medication_reminder_sends_message_with_keyboard() -> None:
    bot = AsyncMock()
    notification = MedicationReminderNotification(42, "Напоминание: принять лекарство")

    await notification.send(bot)

    bot.send_message.assert_awaited_once()
    kwargs = bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == 42
    assert kwargs["text"] == "Напоминание: принять лекарство"
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_notification_queue_processes_enqueued_items() -> None:
    bot = AsyncMock()
    queue = NotificationQueue(bot, rate_limit=0)
    sent = AsyncMock()

    class FakeNotification:
        async def send(self, bot):
            await sent()

    await queue.start()
    await queue.enqueue(FakeNotification())
    await queue.queue.join()
    await queue.stop()

    sent.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_slot_notifications_enqueues_reminders() -> None:
    from adapters.telegram import medication_reminders

    fake_user = MagicMock(id=1, telegram_id=100, timezone="3")
    fake_notification = MagicMock(note="Принять таблетки")

    queue = AsyncMock(spec=NotificationQueue)

    with patch.object(medication_reminders, "SessionLocal") as session_local:
        session = AsyncMock()
        session_local.return_value.__aenter__.return_value = session
        session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[fake_user])))),
                MagicMock(
                    scalars=MagicMock(
                        return_value=MagicMock(all=MagicMock(return_value=[fake_notification]))
                    )
                ),
            ]
        )
        await medication_reminders.process_slot_notifications(queue)

    queue.enqueue.assert_awaited_once()
    enqueued = queue.enqueue.await_args.args[0]
    assert isinstance(enqueued, MedicationReminderNotification)
    assert enqueued.chat_id == 100
    assert "Принять таблетки" in enqueued.text
