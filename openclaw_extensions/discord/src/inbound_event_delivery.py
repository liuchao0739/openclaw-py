"""Discord plugin module implements inbound event delivery behavior."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

ActiveEvent = dict[str, Any]
DiscordInboundEventDeliveryEnd = Callable[[], None]

_REGISTRY: dict[str, ActiveEvent] = {}


def _normalize_discord_delivery_target(value: str) -> str:
    return re.sub(r"^(discord:|channel:)", "", value.strip(), flags=re.IGNORECASE).lower()


def _resolve_discord_inbound_event_delivery_correlation_key(
    session_key: str | None,
    inbound_event_kind: str | None = None,
) -> str | None:
    key = (session_key or "").strip()
    if not key:
        return None
    return f"{key}:room_event" if inbound_event_kind == "room_event" else key


def begin_discord_inbound_event_delivery_correlation(
    session_key: str | None,
    event: ActiveEvent,
    options: dict[str, Any] | None = None,
) -> DiscordInboundEventDeliveryEnd:
    key = _resolve_discord_inbound_event_delivery_correlation_key(
        session_key,
        (options or {}).get("inboundEventKind"),
    )
    if not key:
        return lambda: None
    _REGISTRY[key] = event

    def end() -> None:
        if _REGISTRY.get(key) is event:
            _REGISTRY.pop(key, None)

    return end


def notify_discord_inbound_event_outbound_success(params: dict[str, Any]) -> None:
    key = _resolve_discord_inbound_event_delivery_correlation_key(
        params.get("sessionKey"),
        params.get("inboundEventKind"),
    )
    if not key:
        return
    event = _REGISTRY.get(key)
    if event is None:
        return
    if _normalize_discord_delivery_target(str(event.get("outboundTo") or "")) != _normalize_discord_delivery_target(
        str(params.get("to") or "")
    ):
        return
    outbound_account_id = event.get("outboundAccountId")
    account_id = params.get("accountId")
    if outbound_account_id and account_id and account_id != outbound_account_id:
        return
    mark_delivered = event.get("markInboundEventDelivered")
    if callable(mark_delivered):
        mark_delivered()


def reset_discord_inbound_event_delivery_for_tests() -> None:
    _REGISTRY.clear()


__all__ = [
    "begin_discord_inbound_event_delivery_correlation",
    "notify_discord_inbound_event_outbound_success",
    "reset_discord_inbound_event_delivery_for_tests",
]
