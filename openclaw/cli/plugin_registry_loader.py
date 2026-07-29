from __future__ import annotations

from typing import Any


def load_plugin_registry(path: str | None = None) -> dict:
    return {}


def refresh_plugin_registry(path: str | None = None) -> dict:
    return load_plugin_registry(path)
