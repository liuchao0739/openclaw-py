from __future__ import annotations

from typing import Any


def list_plugins() -> list[dict]:
    return []


def format_plugins_list(plugins: list[dict]) -> str:
    if not plugins:
        return "No plugins installed."
    lines: list[str] = []
    for p in plugins:
        name = p.get("name", "")
        version = p.get("version", "")
        lines.append(f"  {name}@{version}" if version else f"  {name}")
    return "
".join(lines)
