from __future__ import annotations

from typing import Any

from openclaw.channels.ids import CHANNEL_IDS
from openclaw.channels.registry import list_registered_channel_plugin_ids
from openclaw.utils.message_channel_constants import INTERNAL_MESSAGE_CHANNEL
from openclaw.utils.message_channel_core import (
    normalize_message_channel as _normalize_message_channel_core,
)


def normalize_message_channel(raw: str | None = None) -> str | None:
    return _normalize_message_channel_core(raw)


def _list_plugin_channel_ids() -> list[str]:
    return list_registered_channel_plugin_ids() or []


def list_deliverable_message_channels() -> list[str]:
    seen: list[str] = []
    for cid in list(CHANNEL_IDS or []) + _list_plugin_channel_ids():
        if cid not in seen:
            seen.append(cid)
    return seen


def _list_gateway_message_channels() -> list[str]:
    return list_deliverable_message_channels() + [INTERNAL_MESSAGE_CHANNEL]


def is_gateway_message_channel(value: str) -> bool:
    return value in _list_gateway_message_channels()


def is_deliverable_message_channel(value: str) -> bool:
    return value in list_deliverable_message_channels()


def resolve_gateway_message_channel(raw: str | None = None) -> str | None:
    normalized = normalize_message_channel(raw)
    if not normalized:
        return None
    return normalized if is_gateway_message_channel(normalized) else None


def resolve_message_channel(primary: str | None = None, fallback: str | None = None) -> str | None:
    return normalize_message_channel(primary) or normalize_message_channel(fallback)
