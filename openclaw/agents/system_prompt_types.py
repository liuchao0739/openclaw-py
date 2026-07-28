from __future__ import annotations

from typing import Any


def build_system_prompt_types() -> dict[str, Any]:
    return {
        "types": {
            "default": "default",
            "concise": "concise",
            "detailed": "detailed",
            "creative": "creative",
        },
        "defaultType": "default",
    }


def resolve_system_prompt_type(
    config: dict[str, Any] | None = None,
) -> str:
    config = config or {}
    return config.get("systemPromptType", "default")
