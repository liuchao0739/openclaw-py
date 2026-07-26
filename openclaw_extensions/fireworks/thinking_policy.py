"""Fireworks plugin thinking policy helpers."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.fireworks.model_id import is_fireworks_kimi_model_id

FIREWORKS_KIMI_THINKING_PROFILE: dict[str, Any] = {
    "levels": [{"id": "off"}],
    "defaultLevel": "off",
}


def resolve_fireworks_thinking_profile(model_id: str) -> dict[str, Any] | None:
    if not is_fireworks_kimi_model_id(model_id):
        return None
    return dict(FIREWORKS_KIMI_THINKING_PROFILE)
