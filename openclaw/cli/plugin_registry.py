from __future__ import annotations

from typing import Any

PLUGIN_REGISTRY: dict[str, Any] = {}


def register_plugin(name: str, spec: Any) -> None:
    PLUGIN_REGISTRY[name] = spec


def get_plugin(name: str) -> Any:
    return PLUGIN_REGISTRY.get(name)


def list_registered_plugins() -> list[str]:
    return list(PLUGIN_REGISTRY.keys())


def is_plugin_registered(name: str) -> bool:
    return name in PLUGIN_REGISTRY
