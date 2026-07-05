"""Backward-compatible re-exports. Prefer adapters.telegram.notification_queue."""

from adapters.telegram.notification_queue import (
    MedicationReminderNotification,
    NotificationBase,
    NotificationQueue,
    SosMassNotification,
    TrustedContactRequest,
)

__all__ = [
    "MedicationReminderNotification",
    "NotificationBase",
    "NotificationQueue",
    "SosMassNotification",
    "TrustedContactRequest",
]
