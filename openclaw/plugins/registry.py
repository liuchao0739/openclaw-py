from __future__ import annotations

import json
import os
from typing import Any


def resolve_plugin_registry_path() -> str:
    return os.path.join(".openclaw", "plugins", "registry.json")


def load_plugin_registry() -> dict[str, Any]:
    path = resolve_plugin_registry_path()
    if not os.path.exists(path):
        return {"plugins": {}, "version": 1}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"plugins": {}, "version": 1}


def save_plugin_registry(registry: dict[str, Any]) -> None:
    path = resolve_plugin_registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(registry, f, indent=2)


def register_plugin(
    plugin_id: str,
    manifest: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if registry is None:
        registry = load_plugin_registry()
    registry.setdefault("plugins", {})[plugin_id] = {
        "name": manifest.get("name", plugin_id),
        "version": manifest.get("version", "0.0.0"),
        "description": manifest.get("description", ""),
        "entry": manifest.get("entry"),
        "registeredAt": __import__("time").time(),
    }
    save_plugin_registry(registry)
    return registry


def unregister_plugin(
    plugin_id: str,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if registry is None:
        registry = load_plugin_registry()
    registry.get("plugins", {}).pop(plugin_id, None)
    save_plugin_registry(registry)
    return registry
