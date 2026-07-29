from __future__ import annotations

from openclaw.packages.normalization_core import normalize_optional_lowercase_string
from openclaw.channels.ids import normalize_chat_channel_id
from openclaw.channels.registry_normalize import normalize_any_channel_id
from openclaw.utils.message_channel_constants import INTERNAL_MESSAGE_CHANNEL


def normalize_message_channel(raw: str | None = None) -> str | None:
    normalized = normalize_optional_lowercase_string(raw)
    if not normalized:
        return None
    if normalized == INTERNAL_MESSAGE_CHANNEL:
        return INTERNAL_MESSAGE_CHANNEL
    built_in = normalize_chat_channel_id(normalized)
    if built_in:
        return built_in
    return normalize_any_channel_id(normalized) or normalized


def is_deliverable_message_channel(value: str) -> bool:
    normalized = normalize_message_channel(value)
    return normalized is not None and normalized != INTERNAL_MESSAGE_CHANNEL and normalized == value
