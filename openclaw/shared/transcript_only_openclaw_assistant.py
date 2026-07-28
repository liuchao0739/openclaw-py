"""Identifies OpenClaw-authored assistant rows that are transcript bookkeeping."""

from __future__ import annotations

from typing import Any

_TRANSCRIPT_ONLY_OPENCLAW_ASSISTANT_MODELS = {"delivery-mirror", "gateway-injected"}


def is_transcript_only_openclaw_assistant_model(provider: Any, model: Any) -> bool:
    return (
        provider == "openclaw"
        and isinstance(model, str)
        and model in _TRANSCRIPT_ONLY_OPENCLAW_ASSISTANT_MODELS
    )


def is_transcript_only_openclaw_assistant_message(message: Any) -> bool:
    if not isinstance(message, dict):
        return False
    if isinstance(message, list):
        return False
    role = message.get("role")
    provider = message.get("provider")
    model = message.get("model")
    return role == "assistant" and is_transcript_only_openclaw_assistant_model(provider, model)


def is_openclaw_delivery_mirror_assistant_message(message: Any) -> bool:
    if not isinstance(message, dict):
        return False
    if isinstance(message, list):
        return False
    return (
        message.get("role") == "assistant"
        and message.get("provider") == "openclaw"
        and message.get("model") == "delivery-mirror"
    )
