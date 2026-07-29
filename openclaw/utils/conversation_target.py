from __future__ import annotations

from openclaw.utils.message_channel_normalize import (
    normalize_message_channel,
)


def normalize_conversation_id(value: str | int | None) -> str | None:
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            import math

            if not math.isfinite(value):
                return None
        return str(int(value))
    if isinstance(value, str):
        from openclaw.packages.normalization_core import normalize_optional_string

        return normalize_optional_string(value)
    return None


def normalize_conversation_target_params(params: dict) -> dict:
    channel = None
    if isinstance(params.get("channel"), str):
        channel = normalize_message_channel(params["channel"]) or params["channel"].strip()
    conversation_id = normalize_conversation_id(params.get("conversationId"))
    parent_conversation_id = normalize_conversation_id(params.get("parentConversationId"))
    return {
        "channel": channel,
        "conversationId": conversation_id,
        "parentConversationId": parent_conversation_id,
    }
