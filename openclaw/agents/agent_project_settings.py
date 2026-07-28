from __future__ import annotations

from typing import Any


def resolve_agent_project_settings(
    project_dir: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "projectDir": project_dir or ".",
        "config": config or {},
        "provider": None,
        "model": None,
    }


def load_project_settings(project_dir: str) -> dict[str, Any]:
    import json
    import os
    settings_path = os.path.join(project_dir, ".openclaw", "settings.json")
    if not os.path.exists(settings_path):
        return {}
    try:
        with open(settings_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}
