from __future__ import annotations

from typing import Any


DEFAULT_AGENT_RUNTIME_CONFIG: dict[str, Any] = {
    "maxTurns": 50,
    "maxTokens": 128000,
    "temperature": 0.7,
    "topP": 0.9,
    "timeoutMs": 300000,
    "streaming": True,
    "toolsEnabled": True,
    "thinkingEnabled": True,
}


def resolve_agent_runtime_config(
    config: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(DEFAULT_AGENT_RUNTIME_CONFIG)
    if config:
        result.update(config)
    if overrides:
        result.update(overrides)
    return result


def merge_agent_runtime_config(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    return {**base, **override}
