"""DeepSeek plugin thinking profile helpers."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.deepseek.models import is_deep_seek_v4_model_id

V4_THINKING_LEVEL_IDS = (
    "off",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
)

DEEPSEEK_V4_THINKING_PROFILE: dict[str, Any] = {
    "levels": [{"id": level_id} for level_id in V4_THINKING_LEVEL_IDS],
    "defaultLevel": "high",
}


def resolve_deep_seek_v4_thinking_profile(model_id: str) -> dict[str, Any] | None:
    if not is_deep_seek_v4_model_id(model_id):
        return None
    return dict(DEEPSEEK_V4_THINKING_PROFILE)
