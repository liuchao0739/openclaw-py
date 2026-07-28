from __future__ import annotations

from typing import Any


def build_context(
    workspace_dir: str | None = None,
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "workspaceDir": workspace_dir or ".",
        "config": config or {},
        "env": env or {},
        "sessionId": None,
        "messages": [],
        "state": {},
    }


def resolve_context_runtime_state(
    context: dict[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    state = context.get("state", {})
    return state.get(key, default)


def update_context_runtime_state(
    context: dict[str, Any],
    key: str,
    value: Any,
) -> dict[str, Any]:
    context.setdefault("state", {})[key] = value
    return context
