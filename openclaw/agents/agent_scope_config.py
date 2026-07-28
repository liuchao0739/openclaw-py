from __future__ import annotations

from typing import Any


def resolve_agent_scope_config(
    config: dict[str, Any] | None = None,
    workspace_dir: str | None = None,
) -> dict[str, Any]:
    config = config or {}
    return {
        "workspaceDir": workspace_dir or config.get("workspaceDir", "."),
        "agentDir": config.get("agentDir"),
        "provider": config.get("provider"),
        "model": config.get("model"),
    }


def resolve_default_agent_dir() -> str:
    from openclaw.config.paths import resolve_agent_path
    return resolve_agent_path()
