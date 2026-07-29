from __future__ import annotations

from typing import Any


def format_plugin_row(plugin: dict) -> str:
    name = plugin.get("name", "")
    version = plugin.get("version", "")
    status = plugin.get("status", "")
    return f"{name:<30} {version:<15} {status}"


def format_plugins_table(plugins: list[dict]) -> str:
    if not plugins:
        return "No plugins found."
    lines = [format_plugin_row(p) for p in plugins]
    header = format_plugin_row({"name": "NAME", "version": "VERSION", "status": "STATUS"})
    return "
".join([header, *lines])
