from __future__ import annotations

import json
import os
from typing import Any


def resolve_plugin_config_state_path() -> str:
    return os.path.join(".openclaw", "plugins", "config-state.json")


def load_plugin_config_state() -> dict[str, Any]:
    path = resolve_plugin_config_state_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_plugin_config_state(state: dict[str, Any]) -> None:
    path = resolve_plugin_config_state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
