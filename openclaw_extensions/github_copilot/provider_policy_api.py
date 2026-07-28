from __future__ import annotations

from typing import Any

from openclaw_extensions.github_copilot.model_metadata import resolve_copilot_extended_thinking_levels


def resolve_thinking_profile(context: dict[str, Any]) -> dict[str, Any] | None:
    if str(context.get("provider", "")).strip().lower() != "github-copilot":
        return None
    model_id = context.get("modelId", "")
    compat = context.get("compat")
    extended_levels = resolve_copilot_extended_thinking_levels(model_id, compat)
    return {
        "levels": [
            {"id": "off"},
            {"id": "minimal"},
            {"id": "low"},
            {"id": "medium"},
            {"id": "high"},
            *[{"id": level} for level in extended_levels],
        ],
    }
