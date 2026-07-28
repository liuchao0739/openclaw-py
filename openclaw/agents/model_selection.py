from __future__ import annotations

from typing import Any


def build_model_selector(
    config: dict[str, Any] | None = None,
    profiles: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "profiles": profiles or {},
        "selectedModel": None,
        "selectedProfile": None,
    }


def resolve_model_selection(
    provider: str,
    available_models: list[str],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    preferred = config.get("model")
    if preferred and preferred in available_models:
        return {
            "provider": provider,
            "model": preferred,
            "source": "config",
        }
    if available_models:
        return {
            "provider": provider,
            "model": available_models[0],
            "source": "default",
        }
    return {
        "provider": provider,
        "model": None,
        "source": "unavailable",
    }
