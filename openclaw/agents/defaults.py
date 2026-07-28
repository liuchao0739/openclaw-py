from __future__ import annotations

from typing import Any


def build_defaults(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "temperature": 0.7,
        "topP": 0.9,
        "maxTokens": 128000,
        "streaming": True,
        "thinking": True,
        "tools": True,
    }


def resolve_default(key: str, config: dict[str, Any] | None = None) -> Any:
    defaults = build_defaults(config)
    return defaults.get(key)
