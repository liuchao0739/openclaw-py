from __future__ import annotations

import json
import os
from typing import Any

from openclaw.plugins.constants import (
    PLUGIN_COMPAT_DIR,
    PLUGIN_MIGRATION_STATE_FILENAME,
)
from openclaw.plugins.compat_types import (
    PLUGIN_COMPAT_STATUSES,
    PluginCompatStatus,
    normalize_plugin_compat_status,
)


def resolve_plugin_compat_dir() -> str:
    return PLUGIN_COMPAT_DIR


def resolve_plugin_migration_state_path() -> str:
    return os.path.join(resolve_plugin_compat_dir(), PLUGIN_MIGRATION_STATE_FILENAME)


def load_plugin_migration_state() -> dict[str, Any]:
    state_path = resolve_plugin_migration_state_path()
    if not os.path.exists(state_path):
        return {}
    try:
        with open(state_path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_plugin_migration_state(state: dict[str, Any]) -> None:
    state_path = resolve_plugin_migration_state_path()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def get_plugin_compat_status(
    plugin_name: str,
    state: dict[str, Any] | None = None,
) -> str:
    if state is None:
        state = load_plugin_migration_state()
    record = state.get(plugin_name)
    if not record:
        return PluginCompatStatus.COMPAT
    return normalize_plugin_compat_status(record.get("status"))


def set_plugin_compat_status(
    plugin_name: str,
    status: str,
    reason: str | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in PLUGIN_COMPAT_STATUSES:
        raise ValueError(f"Invalid plugin compat status: {status}")
    if state is None:
        state = load_plugin_migration_state()
    record = state.setdefault(plugin_name, {})
    record["status"] = status
    if reason:
        record["reason"] = reason
    import time
    record["updatedAt"] = int(time.time() * 1000)
    save_plugin_migration_state(state)
    return state
