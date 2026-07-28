from typing import Dict, List, Optional
import time

from .notify_state import (
    DEVICE_PAIR_NOTIFY_MAX_SEEN_AGE_MS,
    DEVICE_PAIR_NOTIFY_SEEN_REQUEST_MAX_ENTRIES,
    DEVICE_PAIR_NOTIFY_SEEN_REQUEST_NAMESPACE,
    DEVICE_PAIR_NOTIFY_SUBSCRIBER_MAX_ENTRIES,
    DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE,
    NotifySeenRequest,
    NotifySubscription,
    notify_request_store_key,
    notify_subscriber_key,
    notify_subscriber_store_key,
)
from .api import listDevicePairing, normalize_optional_string

NOTIFY_POLL_INTERVAL_MS = 10_000


def format_string_list(values: Optional[List[str]]) -> str:
    if not values or len(values) == 0:
        return "none"
    normalized = [v.strip() for v in values if v and v.strip()]
    return ", ".join(normalized) if normalized else "none"


def format_role_list(request: Dict) -> str:
    role = normalize_optional_string(request.get("role"))
    if role:
        return role
    return format_string_list(request.get("roles"))


def format_scope_list(request: Dict) -> str:
    return format_string_list(request.get("scopes"))


def format_pending_requests(pending: List[Dict]) -> str:
    if not pending or len(pending) == 0:
        return "No pending device pairing requests."
    lines = ["Pending device pairing requests:"]
    for req in pending:
        label = normalize_optional_string(req.get("displayName")) or req.get("deviceId", "unknown")
        platform = normalize_optional_string(req.get("platform"))
        ip = normalize_optional_string(req.get("remoteIp"))
        parts = [
            f"- {req.get('requestId', 'unknown')}",
            f"name={label}" if label else None,
            f"platform={platform}" if platform else None,
            f"role={format_role_list(req)}",
            f"scopes={format_scope_list(req)}",
            f"ip={ip}" if ip else None,
        ]
        parts = [p for p in parts if p]
        lines.append(" · ".join(parts))
    return "\n".join(lines)


def _open_subscriber_store(api):
    return api.runtime.state.openKeyedStore({
        "namespace": DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE,
        "maxEntries": DEVICE_PAIR_NOTIFY_SUBSCRIBER_MAX_ENTRIES,
    })


def _open_seen_request_store(api):
    return api.runtime.state.openKeyedStore({
        "namespace": DEVICE_PAIR_NOTIFY_SEEN_REQUEST_NAMESPACE,
        "maxEntries": DEVICE_PAIR_NOTIFY_SEEN_REQUEST_MAX_ENTRIES,
        "defaultTtlMs": DEVICE_PAIR_NOTIFY_MAX_SEEN_AGE_MS,
    })


async def _read_notify_state(api) -> Dict:
    subscriber_store = _open_subscriber_store(api)
    seen_request_store = _open_seen_request_store(api)

    subscriber_entries = await subscriber_store.entries()
    seen_request_entries = await seen_request_store.entries()

    subscribers = sorted(
        [entry.value for entry in subscriber_entries],
        key=lambda s: s.added_at_ms,
    )
    notified_request_ids: Dict[str, int] = {}
    for entry in seen_request_entries:
        req_id = normalize_optional_string(entry.value.request_id)
        notified_at_ms = entry.value.notified_at_ms
        if req_id and isinstance(notified_at_ms, (int, float)) and not isinstance(notified_at_ms, bool) and notified_at_ms > 0:
            notified_request_ids[req_id] = int(notified_at_ms)

    return {"subscribers": subscribers, "notifiedRequestIds": notified_request_ids}


async def _write_notify_state(api, state: Dict) -> None:
    subscriber_store = _open_subscriber_store(api)
    seen_request_store = _open_seen_request_store(api)

    next_subscribers = {
        notify_subscriber_store_key(s): s for s in state["subscribers"]
    }
    for entry in await subscriber_store.entries():
        if entry.key not in next_subscribers:
            await subscriber_store.delete(entry.key)
    for key, subscriber in next_subscribers.items():
        await subscriber_store.register(key, subscriber)

    next_seen_requests = {
        notify_request_store_key(req_id): NotifySeenRequest(req_id, notified_at_ms)
        for req_id, notified_at_ms in state["notifiedRequestIds"].items()
    }
    for entry in await seen_request_store.entries():
        if entry.key not in next_seen_requests:
            await seen_request_store.delete(entry.key)
    for key, value in next_seen_requests.items():
        await seen_request_store.register(key, value, {"ttlMs": DEVICE_PAIR_NOTIFY_MAX_SEEN_AGE_MS})


def _resolve_notify_target(ctx: Dict) -> Optional[Dict]:
    to = (
        normalize_optional_string(ctx.get("senderId"))
        or normalize_optional_string(ctx.get("from"))
        or normalize_optional_string(ctx.get("to"))
        or ""
    )
    if not to:
        return None
    result = {"to": to}
    if ctx.get("accountId"):
        result["accountId"] = ctx["accountId"]
    if ctx.get("messageThreadId") is not None:
        result["messageThreadId"] = ctx["messageThreadId"]
    return result


def _upsert_notify_subscriber(
    subscribers: List[NotifySubscription], target: Dict, mode: str
) -> bool:
    target_sub = NotifySubscription(
        to=target["to"],
        mode=mode,
        added_at_ms=int(time.time() * 1000),
        account_id=target.get("accountId"),
        message_thread_id=target.get("messageThreadId"),
    )
    key = notify_subscriber_key(target_sub)
    index = next(
        (i for i, s in enumerate(subscribers) if notify_subscriber_key(s) == key),
        -1,
    )
    if index == -1:
        subscribers.append(target_sub)
        return True
    existing = subscribers[index]
    if existing.mode == mode:
        return False
    subscribers[index] = target_sub
    return True


def _build_pairing_request_notification_text(request: Dict) -> str:
    label = normalize_optional_string(request.get("displayName")) or request.get("deviceId", "unknown")
    platform = normalize_optional_string(request.get("platform"))
    ip = normalize_optional_string(request.get("remoteIp"))
    role = format_role_list(request)
    scopes = format_scope_list(request)
    lines = [
        "📲 New device pairing request",
        f"ID: {request.get('requestId', 'unknown')}",
        f"Name: {label}",
    ]
    if platform:
        lines.append(f"Platform: {platform}")
    lines.extend([f"Role: {role}", f"Scopes: {scopes}"])
    if ip:
        lines.append(f"IP: {ip}")
    lines.extend([
        "",
        f"Approve: /pair approve {request.get('requestId', 'unknown')}",
        "List pending: /pair pending",
    ])
    return "\n".join(lines)


def _request_timestamp_ms(request: Dict) -> Optional[int]:
    ts = request.get("ts")
    if not isinstance(ts, (int, float)) or isinstance(ts, bool) or ts <= 0:
        return None
    return int(ts)


def _should_notify_subscriber_for_request(
    subscriber: NotifySubscription, request: Dict
) -> bool:
    if subscriber.mode != "once":
        return True
    ts = _request_timestamp_ms(request)
    if ts is None:
        return False
    return ts >= subscriber.added_at_ms


async def _notify_subscriber(params: Dict) -> bool:
    api = params["api"]
    subscriber = params["subscriber"]
    text = params["text"]

    try:
        adapter = await api.runtime.channel.outbound.loadAdapter("telegram")
        send = getattr(adapter, "sendText", None) if adapter else None
        if not send:
            api.logger.warn(
                "device-pair: telegram outbound adapter unavailable for pairing notifications"
            )
            return False

        send_params = {
            "cfg": api.config,
            "to": subscriber.to,
            "text": text,
        }
        if subscriber.account_id:
            send_params["accountId"] = subscriber.account_id
        if subscriber.message_thread_id is not None:
            send_params["threadId"] = subscriber.message_thread_id
        await send(send_params)
        return True
    except Exception as err:
        api.logger.warn(
            f"device-pair: failed to send pairing notification to {subscriber.to}: {err}"
        )
        return False


async def _notify_pending_pairing_requests(params: Dict) -> None:
    api = params["api"]
    state = await _read_notify_state(api)
    pairing = await listDevicePairing()
    pending = pairing.get("pending", [])
    now = int(time.time() * 1000)
    pending_ids = {entry.get("requestId") for entry in pending}
    changed = False

    for req_id in list(state["notifiedRequestIds"].keys()):
        if req_id not in pending_ids or now - state["notifiedRequestIds"][req_id] > DEVICE_PAIR_NOTIFY_MAX_SEEN_AGE_MS:
            del state["notifiedRequestIds"][req_id]
            changed = True

    if state["subscribers"]:
        one_shot_delivered = set()
        for request in pending:
            req_id = request.get("requestId")
            if req_id and req_id in state["notifiedRequestIds"]:
                continue

            text = _build_pairing_request_notification_text(request)
            delivered = False
            for subscriber in state["subscribers"]:
                if not _should_notify_subscriber_for_request(subscriber, request):
                    continue
                sent = await _notify_subscriber({"api": api, "subscriber": subscriber, "text": text})
                delivered = delivered or sent
                if sent and subscriber.mode == "once":
                    one_shot_delivered.add(notify_subscriber_key(subscriber))

            if delivered and req_id:
                state["notifiedRequestIds"][req_id] = now
                changed = True

        if one_shot_delivered:
            initial_count = len(state["subscribers"])
            state["subscribers"] = [
                s for s in state["subscribers"]
                if notify_subscriber_key(s) not in one_shot_delivered
            ]
            if len(state["subscribers"]) != initial_count:
                changed = True

    if changed:
        await _write_notify_state(api, state)


async def arm_pair_notify_once(params: Dict) -> bool:
    api = params["api"]
    ctx = params["ctx"]

    if ctx.get("channel") != "telegram":
        return False

    target = _resolve_notify_target(ctx)
    if not target:
        return False

    state = await _read_notify_state(api)
    changed = False

    if _upsert_notify_subscriber(state["subscribers"], target, "once"):
        changed = True

    if changed:
        await _write_notify_state(api, state)

    return True


async def handle_notify_command(params: Dict) -> Dict:
    api = params["api"]
    ctx = params["ctx"]
    action = params["action"]

    if ctx.get("channel") != "telegram":
        return {"text": "Pairing notifications are currently supported only on Telegram."}

    target = _resolve_notify_target(ctx)
    if not target:
        return {"text": "Could not resolve Telegram target for this chat."}

    state = await _read_notify_state(api)
    target_key = notify_subscriber_key(NotifySubscription(
        to=target["to"],
        mode="",
        added_at_ms=0,
        account_id=target.get("accountId"),
        message_thread_id=target.get("messageThreadId"),
    ))
    current = next(
        (s for s in state["subscribers"] if notify_subscriber_key(s) == target_key),
        None,
    )

    if action in ("on", "enable"):
        if _upsert_notify_subscriber(state["subscribers"], target, "persistent"):
            await _write_notify_state(api, state)
        return {
            "text": (
                "✅ Pair request notifications enabled for this Telegram chat.\n"
                "I will ping here when a new device pairing request arrives."
            )
        }

    if action in ("off", "disable"):
        current_index = next(
            (i for i, s in enumerate(state["subscribers"])
             if notify_subscriber_key(s) == target_key),
            -1,
        )
        if current_index != -1:
            del state["subscribers"][current_index]
            await _write_notify_state(api, state)
        return {"text": "✅ Pair request notifications disabled for this Telegram chat."}

    if action in ("once", "arm"):
        await arm_pair_notify_once({"api": api, "ctx": ctx})
        return {
            "text": (
                "✅ One-shot pairing notification armed for this Telegram chat.\n"
                "I will notify on the next new pairing request, then auto-disable."
            )
        }

    if action in ("status", ""):
        pending = await listDevicePairing()
        enabled = bool(current)
        mode = current.mode if current else "off"
        return {
            "text": "\n".join([
                f"Pair request notifications: {'enabled' if enabled else 'disabled'} for this chat.",
                f"Mode: {mode}",
                f"Subscribers: {len(state['subscribers'])}",
                f"Pending requests: {len(pending.get('pending', []))}",
                "",
                "Use /pair notify on|off|once",
            ])
        }

    return {"text": "Usage: /pair notify on|off|once|status"}


def create_pairing_notifier_service(api) -> Dict:
    notify_interval = None

    async def tick():
        await _notify_pending_pairing_requests({"api": api})

    async def start(ctx=None):
        nonlocal notify_interval
        try:
            await tick()
        except Exception as err:
            api.logger.warn(f"device-pair: initial notify poll failed: {err}")

        import asyncio

        async def poll():
            while True:
                await asyncio.sleep(NOTIFY_POLL_INTERVAL_MS / 1000)
                try:
                    await tick()
                except Exception as err:
                    api.logger.warn(f"device-pair: notify poll failed: {err}")

        notify_interval = asyncio.create_task(poll())

    async def stop(ctx=None):
        nonlocal notify_interval
        if notify_interval:
            notify_interval.cancel()
            notify_interval = None

    return {
        "id": "device-pair-notifier",
        "start": start,
        "stop": stop,
    }


def formatPendingRequests(pending: List[Dict]) -> str:
    return format_pending_requests(pending)


async def handleNotifyCommand(params: Dict) -> Dict:
    return await handle_notify_command(params)


async def armPairNotifyOnce(params: Dict) -> bool:
    return await arm_pair_notify_once(params)


def createPairingNotifierService(api) -> Dict:
    return create_pairing_notifier_service(api)


__all__ = [
    "formatPendingRequests",
    "armPairNotifyOnce",
    "handleNotifyCommand",
    "createPairingNotifierService",
]
