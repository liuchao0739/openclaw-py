from __future__ import annotations

from typing import Any


def load_plugins_config(path: str | None = None) -> dict:
    return {}


def save_plugins_config(config: dict, path: str | None = None) -> None:
    pass


def resolve_plugin_config_value(plugin_name: str, key: str) -> Any:
    return None
