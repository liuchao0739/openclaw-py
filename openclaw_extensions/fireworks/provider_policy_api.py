"""Fireworks API module exposes the plugin public contract."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.fireworks.thinking_policy import resolve_fireworks_thinking_profile


def resolve_thinking_profile(params: dict[str, Any]) -> dict[str, Any] | None:
    return resolve_fireworks_thinking_profile(params["modelId"])
