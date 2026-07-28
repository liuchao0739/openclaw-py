import hashlib
import json
import re
from typing import Dict, List, Optional, Union


DEVICE_PAIR_NOTIFY_LEGACY_STATE_FILE = "device-pair-notify.json"
DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE = "notify-subscribers"
DEVICE_PAIR_NOTIFY_SEEN_REQUEST_NAMESPACE = "notify-seen-requests"
DEVICE_PAIR_NOTIFY_SUBSCRIBER_MAX_ENTRIES = 1024
DEVICE_PAIR_NOTIFY_SEEN_REQUEST_MAX_ENTRIES = 4096
DEVICE_PAIR_NOTIFY_MAX_SEEN_AGE_MS = 24 * 60 * 60 * 1000


class NotifySubscription:
    def __init__(
        self,
        to: str,
        mode: str,
        added_at_ms: int,
        account_id: Optional[str] = None,
        message_thread_id: Optional[Union[str, int]] = None,
    ):
        self.to = to
        self.account_id = account_id
        self.message_thread_id = message_thread_id
        self.mode = mode
        self.added_at_ms = added_at_ms


class NotifySeenRequest:
    def __init__(self, request_id: str, notified_at_ms: int):
        self.request_id = request_id
        self.notified_at_ms = notified_at_ms


def normalize_optional_string(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _coerce_message_thread_id(value: object) -> Optional[Union[str, int]]:
    if isinstance(value, str):
        normalized = normalize_optional_string(value)
        return normalized or None
    if isinstance(value, (int, float)):
        if not isinstance(value, bool) and value == int(value):
            return int(value)
    return None


def normalize_legacy_notify_state(raw: object) -> Dict:
    root: Dict = {}
    if isinstance(raw, dict):
        root = raw

    subscribers_raw = root.get("subscribers", [])
    if not isinstance(subscribers_raw, list):
        subscribers_raw = []

    notified_raw = root.get("notifiedRequestIds", {})
    if not isinstance(notified_raw, dict):
        notified_raw = {}

    subscribers: List[NotifySubscription] = []
    for item in subscribers_raw:
        if not isinstance(item, dict):
            continue
        to = normalize_optional_string(item.get("to")) or ""
        if not to:
            continue
        account_id = normalize_optional_string(item.get("accountId"))
        message_thread_id = _coerce_message_thread_id(item.get("messageThreadId"))
        mode = "once" if item.get("mode") == "once" else "persistent"
        added_at_ms_value = item.get("addedAtMs")
        if isinstance(added_at_ms_value, (int, float)) and not isinstance(added_at_ms_value, bool) and added_at_ms_value == int(added_at_ms_value):
            added_at_ms = int(added_at_ms_value)
        else:
            import time
            added_at_ms = int(time.time() * 1000)
        subscribers.append(NotifySubscription(
            to=to,
            account_id=account_id,
            message_thread_id=message_thread_id,
            mode=mode,
            added_at_ms=added_at_ms,
        ))

    notified_request_ids: Dict[str, int] = {}
    for request_id, ts in notified_raw.items():
        normalized = normalize_optional_string(request_id)
        if not normalized:
            continue
        if not isinstance(ts, (int, float)) or isinstance(ts, bool) or not (ts > 0):
            continue
        notified_request_ids[normalized] = int(ts)

    return {"subscribers": subscribers, "notifiedRequestIds": notified_request_ids}


def normalize_notify_thread_key(message_thread_id: Optional[Union[str, int]] = None) -> str:
    if isinstance(message_thread_id, (int, float)) and int(message_thread_id) == message_thread_id:
        return str(int(message_thread_id))
    if not isinstance(message_thread_id, str):
        return ""
    normalized = normalize_optional_string(message_thread_id)
    if not normalized:
        return ""
    if not re.fullmatch(r"-?\d+", normalized):
        return normalized
    try:
        return str(int(normalized))
    except ValueError:
        return normalized


def notify_subscriber_key(subscriber: Union[NotifySubscription, Dict]) -> str:
    if isinstance(subscriber, dict):
        to = subscriber.get("to", "")
        account_id = subscriber.get("accountId", "") or ""
        thread_id = normalize_notify_thread_key(subscriber.get("messageThreadId"))
    else:
        to = subscriber.to
        account_id = subscriber.account_id or ""
        thread_id = normalize_notify_thread_key(subscriber.message_thread_id)
    return json.dumps([to, account_id, thread_id])


def _hash_store_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def notify_subscriber_store_key(subscriber: Union[NotifySubscription, Dict]) -> str:
    return _hash_store_key(notify_subscriber_key(subscriber))


def notify_request_store_key(request_id: str) -> str:
    return _hash_store_key(request_id)


__all__ = [
    "DEVICE_PAIR_NOTIFY_LEGACY_STATE_FILE",
    "DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE",
    "DEVICE_PAIR_NOTIFY_SEEN_REQUEST_NAMESPACE",
    "DEVICE_PAIR_NOTIFY_SUBSCRIBER_MAX_ENTRIES",
    "DEVICE_PAIR_NOTIFY_SEEN_REQUEST_MAX_ENTRIES",
    "DEVICE_PAIR_NOTIFY_MAX_SEEN_AGE_MS",
    "NotifySubscription",
    "NotifySeenRequest",
    "normalize_legacy_notify_state",
    "normalize_notify_thread_key",
    "notify_subscriber_key",
    "notify_subscriber_store_key",
    "notify_request_store_key",
]
