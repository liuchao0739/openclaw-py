from typing import Dict, Optional


DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE = "device-pair-notify-subscriber"
DEVICE_PAIR_NOTIFY_SEEN_REQUEST_NAMESPACE = "device-pair-notify-seen"
DEVICE_PAIR_NOTIFY_SUBSCRIBER_MAX_ENTRIES = 32
DEVICE_PAIR_NOTIFY_SEEN_REQUEST_MAX_ENTRIES = 256
DEVICE_PAIR_NOTIFY_MAX_SEEN_AGE_MS = 10 * 60 * 1000


class NotifySubscription:
    def __init__(self, to: str, mode: str, added_at_ms: int, account_id: Optional[str] = None, message_thread_id: Optional[str] = None):
        self.to = to
        self.account_id = account_id
        self.message_thread_id = message_thread_id
        self.mode = mode
        self.added_at_ms = added_at_ms


class NotifySeenRequest:
    def __init__(self, request_id: str, notified_at_ms: int):
        self.request_id = request_id
        self.notified_at_ms = notified_at_ms


def notifySubscriberKey(subscriber: NotifySubscription) -> str:
    parts = [subscriber.to]
    if subscriber.account_id:
        parts.append(subscriber.account_id)
    if subscriber.message_thread_id is not None:
        parts.append(str(subscriber.message_thread_id))
    return "-".join(parts)


def notifySubscriberStoreKey(subscriber: NotifySubscription) -> str:
    return subscriber.to


def notifyRequestStoreKey(request_id: str) -> str:
    return request_id

__all__ = [
    "DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE",
    "DEVICE_PAIR_NOTIFY_SEEN_REQUEST_NAMESPACE",
    "DEVICE_PAIR_NOTIFY_SUBSCRIBER_MAX_ENTRIES",
    "DEVICE_PAIR_NOTIFY_SEEN_REQUEST_MAX_ENTRIES",
    "DEVICE_PAIR_NOTIFY_MAX_SEEN_AGE_MS",
    "NotifySubscription",
    "NotifySeenRequest",
    "notifySubscriberKey",
    "notifySubscriberStoreKey",
    "notifyRequestStoreKey",
]