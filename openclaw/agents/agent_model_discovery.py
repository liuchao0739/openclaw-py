from __future__ import annotations

from typing import Any


def resolve_agent_model_discovery(
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    config = config or {}
    env = env or {}
    models: list[dict[str, Any]] = []

    for model_cfg in config.get("models", []):
        if isinstance(model_cfg, dict):
            models.append(model_cfg)

    return models


def discover_agent_providers(
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> list[str]:
    config = config or {}
    env = env or {}
    providers: set[str] = set()

    for key in env:
        if key.endswith("_API_KEY"):
            providers.add(key.replace("_API_KEY", "").lower())

    for provider in config.get("providers", {}):
        providers.add(provider)

    return sorted(providers)
