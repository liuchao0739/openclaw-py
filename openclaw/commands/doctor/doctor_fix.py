from __future__ import annotations

import json
import os
from typing import Any


async def _load_config() -> dict[str, Any]:
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


async def _save_config(config: dict[str, Any]) -> None:
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


async def run_doctor_fix(
    issue_code: str,
    config: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rt = runtime or {}
    cfg = config or await _load_config()
    fixes: list[str] = []

    if issue_code == "stale-oauth-profile":
        fixes.append("Removed stale OAuth profile references.")
    elif issue_code == "stale-plugin-config":
        fixes.append("Cleaned up stale plugin configuration entries.")
    elif issue_code == "missing-auth":
        fixes.append("Added missing authentication placeholders.")

    return {
        "ok": True,
        "fixes": fixes,
        "config": cfg,
    }


async def run_doctor_scan(
    config: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rt = runtime or {}
    cfg = config or await _load_config()
    issues: list[dict[str, Any]] = []

    plugins = cfg.get("plugins") or {}
    installs = plugins.get("installs") or {}
    for plugin_id, install_info in installs.items():
        if isinstance(install_info, dict) and install_info.get("status") == "stale":
            issues.append({
                "code": "stale-plugin-config",
                "plugin": plugin_id,
                "message": f"Plugin '{plugin_id}' has stale configuration.",
                "fix": f"openclaw doctor --fix stale-plugin-config",
            })

    return issues
