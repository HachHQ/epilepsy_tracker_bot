"""Backward-compatible re-exports. Prefer adapters.telegram.medication_reminders."""

from adapters.telegram.medication_reminders import (
    process_slot_notifications,
    schedule_notification_slots,
    scheduler,
)
from services.medication_slots import get_nearest_slot

__all__ = [
    "get_nearest_slot",
    "process_slot_notifications",
    "schedule_notification_slots",
    "scheduler",
]
